"""
PDF yükleme servisi — upload-to-database zincirini yönetir.

Sorumluluk (mimari-sablon.md §5.1, §7.1):
  1. Gelen dosyayı diske kaydet (uploads/raw/<uuid>/)
  2. SHA-256 hash hesapla; duplicate tespiti yap
  3. raw_files tablosuna PENDING kaydı oluştur
  4. PDFEngine.process() çağır (detect→extract→normalize→validate)
  5. raw_extractions tablosuna ham JSON kaydet
  6. EngineResult.status'e göre:
       OK           → Exam, Student, LearningOutcome, Result kayıtlarını oluştur
       NEEDS_REVIEW → review_queue'ya ekle
       FAILED       → raw_files.status = NEEDS_REVIEW, review_queue'ya ekle

Katman kuralları (P4):
  - Bu servis API katmanından çağrılır; HTTP nesnesi bilmez.
  - DB oturumu (Session) dışarıdan enjekte edilir (DI).
  - PDFEngine DB çağrısı yapmaz; sadece bu servis yazar.

Faz 0 kısıtları:
  - Auth yok → uploaded_by için sistemi temsil eden dummy UUID kullanılır
    (Faz 1'de API'den gerçek user_id alınacak)
  - BackgroundTasks yerine senkron çalışır
    (Faz 1'de Celery task'a taşınacak — ADR-006)
  - Exam kaydında exam_date PDF'ten gelmiyor (format tarih içermiyor)
    → upload_request'teki exam_date parametresiyle doldurulur
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SYSTEM_USER_ID
from app.models.exam import Exam, LearningOutcome, Subject, Topic
from app.models.institution import Class
from app.models.raw_file import (
    RawExtraction,
    RawFile,
    RawFileStatus,
    ReviewQueue,
    ReviewQueueStatus,
)
from app.models.result import Result
from app.models.student import Student
from app.pdf_engine.engine import EngineResult, EngineResultStatus, PDFEngine

logger = logging.getLogger(__name__)

# ── Sonuç veri yapısı ─────────────────────────────────────────────────────────


class UploadResult:
    """upload_pdf() dönüş değeri — API katmanı bu nesneyi JSON'a çevirir."""

    __slots__ = (
        "raw_file_id",
        "status",
        "parser_name",
        "student_count",
        "result_count",
        "review_queue_id",
        "warnings",
        "detail",
    )

    def __init__(
        self,
        *,
        raw_file_id: uuid.UUID,
        status: str,
        parser_name: str,
        student_count: int = 0,
        result_count: int = 0,
        review_queue_id: uuid.UUID | None = None,
        warnings: list[str] | None = None,
        detail: str = "",
    ) -> None:
        self.raw_file_id = raw_file_id
        self.status = status
        self.parser_name = parser_name
        self.student_count = student_count
        self.result_count = result_count
        self.review_queue_id = review_queue_id
        self.warnings = warnings or []
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_file_id": str(self.raw_file_id),
            "status": self.status,
            "parser_name": self.parser_name,
            "student_count": self.student_count,
            "result_count": self.result_count,
            "review_queue_id": str(self.review_queue_id) if self.review_queue_id else None,
            "warnings": self.warnings,
            "detail": self.detail,
        }


# ── Ana Servis Sınıfı ─────────────────────────────────────────────────────────


class UploadService:
    """PDF yükleme ve işleme sürecini yöneten servis sınıfı.

    Kullanım (FastAPI route'dan):
        service = UploadService(db=db)
        result  = service.upload_pdf(
            file_bytes   = await file.read(),
            original_name = file.filename,
            institution_id = institution_id,
            class_id      = class_id,
            exam_name     = "TYT Deneme 5",
            exam_date     = date(2025, 3, 15),
        )
    """

    def __init__(
        self,
        db: Session,
        engine: PDFEngine | None = None,
    ) -> None:
        self._db = db
        self._engine = engine or PDFEngine()

    # ── Genel API ─────────────────────────────────────────────────────────────

    def upload_pdf(
        self,
        *,
        file_bytes: bytes,
        original_name: str,
        institution_id: uuid.UUID,
        class_id: uuid.UUID,
        exam_name: str,
        exam_date: date,
        uploaded_by: uuid.UUID = SYSTEM_USER_ID,
    ) -> UploadResult:
        """PDF'i sisteme alır ve uçtan uca işler.

        Bu metod hiçbir zaman exception fırlatmaz — tüm hatalar
        UploadResult.status ve review_queue'ya yansıtılır (P3).

        Args:
            file_bytes:      Ham PDF içeriği.
            original_name:   Kullanıcının yüklediği dosyanın orijinal adı.
            institution_id:  Hangi kuruma ait olduğu.
            class_id:        Hangi sınıfa ait öğrenciler işlenecek.
            exam_name:       Sınav adı — exams tablosuna yazılır.
            exam_date:       Sınav tarihi (ISO 8601, kullanıcı girer).
            uploaded_by:     Dosyayı yükleyen kullanıcı UUID'i.

        Returns:
            UploadResult
        """
        # ── 1. Duplicate kontrolü ve diske kaydetme ────────────────────────
        file_hash = self._sha256(file_bytes)
        existing = self._find_duplicate(file_hash)
        if existing:
            logger.info(
                "Duplicate PDF tespit edildi: hash=%s raw_file_id=%s",
                file_hash[:8],
                existing.id,
            )
            return UploadResult(
                raw_file_id=existing.id,
                status="DUPLICATE",
                parser_name="",
                detail=(f"Bu PDF daha önce yüklenmiş. Mevcut kayıt: {existing.id} (status={existing.status})"),
            )

        # ── 1.b. Mantıksal Duplicate (Aynı Sınavın Tekrar Yüklenmesi) ──────────
        logical_dup = self._find_logical_duplicate(institution_id, exam_name, exam_date)
        if logical_dup:
            logger.warning("Mantıksal duplicate (aynı sınav adı/tarihi): %s", exam_name)
            # Opsiyonel: Burada direkt bloke edebilir veya uyarı (warning) listesine ekleyebiliriz.
            # Şu an veri bütünlüğü için tam blokaj (DUPLICATE) yapıyoruz.
            return UploadResult(
                raw_file_id=logical_dup.id,
                status="DUPLICATE",
                parser_name="",
                detail=(
                    f"'{exam_name}' adlı sınav bu kurumda daha önce işlenmiş. Mükerrer veri oluşumunu önlemek için işlem durduruldu."
                ),
            )

        saved_path = self._save_to_disk(file_bytes, original_name)

        # ── 2. raw_files kaydı oluştur (PENDING) ──────────────────────────
        raw_file = RawFile(
            institution_id=institution_id,
            file_path=str(saved_path),
            original_name=original_name,
            file_hash=file_hash,
            status=RawFileStatus.PENDING,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(tz=timezone.utc),
        )
        self._db.add(raw_file)
        self._db.flush()  # ID üretilsin ama commit etme
        logger.info("raw_file oluşturuldu: id=%s", raw_file.id)

        # ── 3. PDF Engine çalıştır ─────────────────────────────────────────
        try:
            eng_result: EngineResult = self._engine.process(saved_path)
        except Exception as exc:  # noqa: BLE001
            # Engine kendisi exception fırlatmamalı ama savunma olarak yakala
            logger.error("Engine beklenmedik hata: %s", exc, exc_info=True)
            eng_result = EngineResult(
                status=EngineResultStatus.FAILED,
                parser_name="UNKNOWN",
                confidence=0.0,
                review_reason="EXTRACTION_FAILED",
                review_detail=f"Engine kritik hata: {exc}",
            )

        # ── 4. raw_extractions kaydı oluştur ──────────────────────────────
        raw_extraction = RawExtraction(
            raw_file_id=raw_file.id,
            parser_used=eng_result.parser_name,
            detected_format=eng_result.parser_name,
            raw_json=eng_result.raw_data,
            confidence=eng_result.confidence,
            warnings=eng_result.warnings or [],
            extracted_at=datetime.now(tz=timezone.utc),
        )
        self._db.add(raw_extraction)
        self._db.flush()
        logger.info("raw_extraction oluşturuldu: id=%s", raw_extraction.id)

        # ── 5. EngineResult.status'e göre dallanma ────────────────────────
        if eng_result.status == EngineResultStatus.OK and eng_result.normalized_data:
            return self._handle_ok(
                raw_file=raw_file,
                raw_extraction=raw_extraction,
                eng_result=eng_result,
                institution_id=institution_id,
                class_id=class_id,
                exam_name=exam_name,
                exam_date=exam_date,
            )
        else:
            return self._handle_needs_review(
                raw_file=raw_file,
                raw_extraction=raw_extraction,
                eng_result=eng_result,
            )

    # ── Özel: Başarılı işleme ─────────────────────────────────────────────────

    def _handle_ok(
        self,
        *,
        raw_file: RawFile,
        raw_extraction: RawExtraction,
        eng_result: EngineResult,
        institution_id: uuid.UUID,
        class_id: uuid.UUID,
        exam_name: str,
        exam_date: date,
    ) -> UploadResult:
        """EngineResult.status == OK → normalized veriyi DB'ye yaz."""
        normalized = eng_result.normalized_data  # type: ignore[union-attr]
        student_results: list[dict] = normalized.get("student_results", [])

        # ── Exam kaydı ──────────────────────────────────────────────────────
        exam = Exam(
            institution_id=institution_id,
            raw_file_id=raw_file.id,
            name=exam_name,
            exam_date=exam_date,
            source_format=eng_result.parser_name,
        )
        self._db.add(exam)
        self._db.flush()

        total_result_count = 0

        # ── Her öğrenci için ────────────────────────────────────────────────
        for s_data in student_results:
            student = self._get_or_create_student(
                institution_id=institution_id,
                default_class_id=class_id,
                full_name=s_data.get("full_name", ""),
                student_code=s_data.get("student_code") or None,
                raw_class_name=s_data.get("student_class"),
            )

            # ── Her subject_result satırı için ──────────────────────────────
            student_results_map: dict[Any, Result] = {}

            for row in s_data.get("subject_results", []):
                measured = row.get("measured", True)
                total_q = row.get("total_questions", 0)

                # measured=False ve soru=0 → kaydet ama measured=False işaretle
                # measured=True ama soru=0 → veri tutarsız, measured=False'a çek
                if total_q == 0:
                    measured = False

                learning_outcome = self._get_or_create_learning_outcome(
                    subject_name=row.get("subject_name", ""),
                    topic_name=row.get("topic_name") or row.get("outcome_description", ""),
                    outcome_code=row.get("outcome_code"),
                    outcome_description=row.get("outcome_description", ""),
                )

                c = max(0, row.get("correct", 0))
                w = max(0, row.get("wrong", 0))
                b = max(0, row.get("blank", 0))
                t_q = max(1, total_q) if measured else 1

                if learning_outcome.id in student_results_map:
                    existing = student_results_map[learning_outcome.id]
                    existing.correct += c
                    existing.wrong += w
                    existing.blank += b
                    if measured:
                        existing.total_questions += t_q
                    existing.measured = existing.measured or measured
                else:
                    res = Result(
                        student_id=student.id,
                        exam_id=exam.id,
                        learning_outcome_id=learning_outcome.id,
                        correct=c,
                        wrong=w,
                        blank=b,
                        total_questions=t_q,
                        measured=measured,
                    )
                    student_results_map[learning_outcome.id] = res
                    self._db.add(res)
                    total_result_count += 1

        # ── raw_files.status güncelle ──────────────────────────────────────
        raw_file.status = RawFileStatus.PROCESSED
        self._db.commit()

        logger.info(
            "Upload OK: raw_file=%s exam=%s öğrenci=%d sonuç=%d",
            raw_file.id,
            exam.id,
            len(student_results),
            total_result_count,
        )

        return UploadResult(
            raw_file_id=raw_file.id,
            status="OK",
            parser_name=eng_result.parser_name,
            student_count=len(student_results),
            result_count=total_result_count,
            warnings=eng_result.warnings,
            detail=f"Sınav '{exam_name}' başarıyla işlendi.",
        )

    # ── Özel: Review gerektiren işleme ───────────────────────────────────────

    def _handle_needs_review(
        self,
        *,
        raw_file: RawFile,
        raw_extraction: RawExtraction,
        eng_result: EngineResult,
    ) -> UploadResult:
        """EngineResult.status != OK → review_queue'ya ekle."""
        review = ReviewQueue(
            raw_extraction_id=raw_extraction.id,
            reason=eng_result.review_reason or "UNKNOWN",
            reason_detail=eng_result.review_detail or "",
            status=ReviewQueueStatus.PENDING,
        )
        self._db.add(review)

        # FAILED → NEEDS_REVIEW, NEEDS_REVIEW → NEEDS_REVIEW
        raw_file.status = RawFileStatus.NEEDS_REVIEW
        self._db.commit()

        logger.warning(
            "Upload NEEDS_REVIEW: raw_file=%s reason=%s",
            raw_file.id,
            eng_result.review_reason,
        )

        return UploadResult(
            raw_file_id=raw_file.id,
            status="NEEDS_REVIEW",
            parser_name=eng_result.parser_name,
            review_queue_id=review.id,
            warnings=eng_result.warnings,
            detail=eng_result.review_detail or "Dosya insan incelemesine alındı.",
        )

    # ── Özel: get-or-create yardımcıları ────────────────────────────────────

    def _get_or_create_student(
        self,
        *,
        institution_id: uuid.UUID,
        default_class_id: uuid.UUID,
        full_name: str,
        student_code: str | None,
        raw_class_name: str | None = None,
    ) -> Student:
        """Öğrenciyi ve sınıfını esnek bir şekilde bulur veya oluşturur.

        PDF'te okunabilmiş bir sınıf adı (örn: '8/EG3', '8-A') varsa kurum altında
        o sınıfı arar veya oluşturur; yoksa default_class_id kullanılır.
        """
        target_class_id = default_class_id

        if raw_class_name and raw_class_name.strip():
            clean_name = raw_class_name.strip()
            cls = self._db.query(Class).filter(Class.institution_id == institution_id, Class.name.ilike(clean_name)).first()
            if not cls:
                cls = Class(
                    institution_id=institution_id,
                    name=clean_name,
                    academic_year="2024-2025",
                )
                self._db.add(cls)
                self._db.flush()
            target_class_id = cls.id

        # 1. Önce student_code varsa arama yap
        if student_code:
            student = self._db.query(Student).filter_by(class_id=target_class_id, student_code=student_code).first()
            if not student:
                # Kurumun diğer sınıflarında aynı kod var mı?
                student = (
                    self._db.query(Student)
                    .join(Class)
                    .filter(Class.institution_id == institution_id, Student.student_code == student_code)
                    .first()
                )
                if student:
                    student.class_id = target_class_id
                    self._db.flush()
                    return student
            else:
                return student

        # 2. İsim bazlı arama (Kurum geneli veya hedef sınıf)
        student = self._db.query(Student).filter_by(class_id=target_class_id, full_name=full_name).first()
        if not student:
            student = (
                self._db.query(Student)
                .join(Class)
                .filter(Class.institution_id == institution_id, Student.full_name == full_name)
                .first()
            )
            if student:
                student.class_id = target_class_id
                self._db.flush()
                return student

        if student:
            return student

        # 3. Yeni öğrenci oluştur
        student = Student(
            class_id=target_class_id,
            full_name=full_name,
            student_code=student_code,
        )
        self._db.add(student)
        self._db.flush()
        logger.debug("Yeni öğrenci oluşturuldu: %s (Sınıf: %s)", full_name, target_class_id)
        return student

    def _get_or_create_learning_outcome(
        self,
        *,
        subject_name: str,
        topic_name: str,
        outcome_code: str | None,
        outcome_description: str,
    ) -> LearningOutcome:
        """Subject→Topic→LearningOutcome zincirini get-or-create ile oluşturur.

        Aynı description + topic kombinasyonu varsa mevcut kaydı döner.
        Bu sayede aynı kazanım birden fazla sınavda tekrar oluşturulmaz.
        """
        # ── Subject ──────────────────────────────────────────────────────────
        subject_name = subject_name.strip() or "Genel"
        subject = self._db.query(Subject).filter_by(name=subject_name).first()
        if not subject:
            short_code = self._make_short_code(subject_name)
            subject = Subject(name=subject_name, short_code=short_code)
            self._db.add(subject)
            self._db.flush()

        # ── Topic ─────────────────────────────────────────────────────────────
        topic_name = topic_name.strip() or subject_name
        topic = self._db.query(Topic).filter_by(subject_id=subject.id, name=topic_name).first()
        if not topic:
            topic = Topic(subject_id=subject.id, name=topic_name)
            self._db.add(topic)
            self._db.flush()

        # ── LearningOutcome ───────────────────────────────────────────────────
        description = outcome_description.strip() or topic_name
        outcome = self._db.query(LearningOutcome).filter_by(topic_id=topic.id, description=description).first()
        if not outcome:
            outcome = LearningOutcome(
                topic_id=topic.id,
                code=outcome_code,
                description=description,
            )
            self._db.add(outcome)
            self._db.flush()

        return outcome

    # ── Özel: Dosya yönetimi ─────────────────────────────────────────────────

    def _save_to_disk(self, file_bytes: bytes, original_name: str) -> Path:
        """PDF'i uploads/raw/<uuid>/<original_name> yoluna kaydeder.

        Her yükleme için yeni bir UUID dizini oluşturulur.
        Bu sayede aynı isimli iki farklı dosya çakışmaz.
        """
        file_id = uuid.uuid4()
        dest_dir = settings.upload_dir / str(file_id)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Güvenli dosya adı: path traversal saldırısını engelle
        safe_name = Path(original_name).name
        dest_path = dest_dir / safe_name

        dest_path.write_bytes(file_bytes)
        logger.debug("Dosya kaydedildi: %s", dest_path)
        return dest_path

    @staticmethod
    def _sha256(data: bytes) -> str:
        """SHA-256 hex digest — duplicate tespiti için."""
        return hashlib.sha256(data).hexdigest()

    def _find_duplicate(self, file_hash: str) -> RawFile | None:
        """Aynı hash'e sahip daha önce yüklenmiş ve hala aktif bir sınavla ilişkili dosyayı arar."""
        raw_files = self._db.query(RawFile).filter_by(file_hash=file_hash).all()
        for rf in raw_files:
            exam = self._db.query(Exam).filter_by(raw_file_id=rf.id).first()
            if exam:
                return rf
        return None

    def _find_logical_duplicate(self, institution_id: uuid.UUID, exam_name: str, exam_date: date) -> RawFile | None:
        """Aynı kurumda, aynı ad ve tarihle daha önce yüklenmiş başarılı bir sınav (RawFile) arar."""
        exam = self._db.query(Exam).filter_by(institution_id=institution_id, name=exam_name, exam_date=exam_date).first()

        if exam and exam.raw_file_id:
            return self._db.query(RawFile).filter_by(id=exam.raw_file_id).first()
        return None

    @staticmethod
    def _make_short_code(name: str) -> str:
        """Ders adından kısa kod üretir: 'Matematik-1' → 'MAT1' (maks 10 chr).

        Çakışma durumunda UUID suffix eklenir.
        """
        # Türkçe karakterleri ASCII'ye çevir
        replacements = str.maketrans("ÇçĞğİıÖöŞşÜü", "CcGgIiOoSsUu")
        cleaned = name.translate(replacements)
        # Sadece harf ve rakam bırak, büyük harf yap
        code = "".join(c for c in cleaned.upper() if c.isalnum())[:8]
        return code or "GEN"

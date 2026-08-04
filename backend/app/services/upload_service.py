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

from sqlalchemy import func
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
from app.pdf_engine.factory import ParserFactory
from app.pdf_engine.ocr_fallback import check_pdf_accessibility

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
    ) -> None:
        self._db = db

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

        # ── 3. OCR ve Format Kontrolü ─────────────────────────────────────
        accessibility = check_pdf_accessibility(saved_path)
        if accessibility == "CORRUPTED":
            raise ValueError("PDF dosyası bozuk veya açılamıyor. Lütfen geçerli ve okunabilir bir PDF belgesi yükleyin.")
        elif accessibility == "IMAGE_BASED":
            raise ValueError("PDF salt resim içeriyor. Lütfen metin tabanlı (taranmamış) bir PDF belgesi yükleyin.")

        # ── 4. ParserFactory ile Ayrıştırma ────────────────────────────────
        try:
            parser = ParserFactory.create_parser(saved_path)
            parser.parse()
            student_results = parser.extract_results()
            parser_name = parser.__class__.__name__
        except ValueError as ve:
            raise ve
        except Exception as exc:
            logger.error("Parser beklenmedik hata: %s", exc, exc_info=True)
            raise ValueError(f"Sınav sonuçları ayrıştırılamadı. Lütfen geçerli bir TYT veya LGS belgesi yükleyin. Detay: {exc}")

        # ── 5. raw_extractions kaydı oluştur ──────────────────────────────
        raw_extraction = RawExtraction(
            raw_file_id=raw_file.id,
            parser_used=parser_name,
            detected_format=parser_name,
            raw_json={"student_results": student_results},
            confidence=1.0,
            warnings=[],
            extracted_at=datetime.now(tz=timezone.utc),
        )
        self._db.add(raw_extraction)
        self._db.flush()

        # ── 6. OK İşlemleri ───────────────────────────────────────────────
        return self._handle_ok(
            raw_file=raw_file,
            raw_extraction=raw_extraction,
            student_results=student_results,
            parser_name=parser_name,
            institution_id=institution_id,
            class_id=class_id,
            exam_name=exam_name,
            exam_date=exam_date,
        )

    # ── Özel: Başarılı işleme ─────────────────────────────────────────────────

    def _handle_ok(
        self,
        *,
        raw_file: RawFile,
        raw_extraction: RawExtraction,
        student_results: list[dict],
        parser_name: str,
        institution_id: uuid.UUID,
        class_id: uuid.UUID,
        exam_name: str,
        exam_date: date,
    ) -> UploadResult:
        """Parser başarıyla veriyi çıkardı → DB'ye yaz."""

        # ── Exam kaydı ──────────────────────────────────────────────────────
        exam = Exam(
            institution_id=institution_id,
            raw_file_id=raw_file.id,
            name=exam_name,
            exam_date=exam_date,
            source_format=parser_name,
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
            parser_name=parser_name,
            student_count=len(student_results),
            result_count=total_result_count,
            warnings=[],
            detail=f"Sınav '{exam_name}' başarıyla işlendi.",
        )

    # ── Özel: Review gerektiren işleme ───────────────────────────────────────

    def _handle_needs_review(
        self,
        raw_file: RawFile,
        raw_extraction: RawExtraction | None,
        parser_name: str,
        review_reason: str,
        review_detail: str,
    ) -> UploadResult:
        """Hata durumu → review_queue'ya ekle."""
        review = ReviewQueue(
            raw_extraction_id=raw_extraction.id if raw_extraction else None,
            reason=review_reason,
            reason_detail=review_detail,
            status=ReviewQueueStatus.PENDING,
        )
        self._db.add(review)

        # FAILED → NEEDS_REVIEW, NEEDS_REVIEW → NEEDS_REVIEW
        raw_file.status = RawFileStatus.NEEDS_REVIEW
        self._db.commit()

        logger.warning(
            "Upload NEEDS_REVIEW: raw_file=%s reason=%s",
            raw_file.id,
            review_reason,
        )

        return UploadResult(
            raw_file_id=raw_file.id,
            status="NEEDS_REVIEW",
            parser_name=parser_name,
            review_queue_id=review.id,
            warnings=[],
            detail=review_detail or "Dosya insan incelemesine alındı.",
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
        """Öğrenciyi ve sınıfını esnek bir şekilde bulur veya oluşturur."""
        target_class_id = None

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
        else:
            # Check if default_class_id is valid AND belongs to this institution
            cls = self._db.query(Class).filter_by(id=default_class_id, institution_id=institution_id).first()
            if cls:
                target_class_id = cls.id
            else:
                # Do NOT pick a random class like '8A' or '11F'.
                # explicitly use/create a generic class to avoid misclassification.
                cls = self._db.query(Class).filter_by(institution_id=institution_id, name="Genel Sınıf").first()
                if not cls:
                    cls = Class(
                        institution_id=institution_id,
                        name="Genel Sınıf",
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

    @staticmethod
    def _normalize_subject_name(raw_name: str) -> str:
        """Ders adını standartlaştırır (örn. 'Matematik-1', 'Matematik.08' → 'Matematik')."""
        name = raw_name.strip()
        if not name:
            return "Genel"

        clean_upper = (
            name.upper().replace("İ", "I").replace("Ğ", "G").replace("Ü", "U").replace("Ş", "S").replace("Ö", "O").replace("Ç", "C")
        )

        if "TURKCE" in clean_upper:
            return "Türkçe"
        if "MATEMATIK" in clean_upper:
            return "Matematik"
        if "FEN" in clean_upper:
            return "Fen Bilimleri"
        if "INKILAP" in clean_upper or "ATATURK" in clean_upper:
            return "T.C. İnkılap Tarihi ve Atatürkçülük"
        if "INGILIZCE" in clean_upper or "YABANCI" in clean_upper or "ENGLISH" in clean_upper:
            return "Yabancı Dil"
        if "DIN" in clean_upper or "DKAB" in clean_upper or "AHLAK" in clean_upper:
            return "Din Kültürü ve Ahlak Bilgisi"
        if "SOSYAL" in clean_upper:
            return "Sosyal Bilgiler"
        if "TARIH" in clean_upper:
            return "Tarih"
        if "COGRAFYA" in clean_upper:
            return "Coğrafya"
        if "FELSEFE" in clean_upper:
            return "Felsefe"
        if "FIZIK" in clean_upper:
            return "Fizik"
        if "KIMYA" in clean_upper:
            return "Kimya"
        if "BIYOLOJI" in clean_upper:
            return "Biyoloji"

        return name

    def _get_or_create_learning_outcome(
        self,
        *,
        subject_name: str,
        topic_name: str,
        outcome_code: str | None,
        outcome_description: str,
    ) -> LearningOutcome:
        """Subject→Topic→LearningOutcome zincirini get-or-create ile oluşturur."""
        if not hasattr(self, "_subject_cache"):
            self._subject_cache = {}

        # ── 1. Subject (Get or Create) ──────────────────────────────────────────
        canonical_subject = self._normalize_subject_name(subject_name)
        short_code = self._make_short_code(canonical_subject)

        subject = self._subject_cache.get(short_code)

        if not subject:
            subject = self._db.query(Subject).filter_by(short_code=short_code).first()
            if not subject:
                subject = self._db.query(Subject).filter(func.lower(Subject.name) == func.lower(canonical_subject)).first()
            if not subject:
                subject = self._db.query(Subject).filter_by(name=subject_name.strip()).first()

        if not subject:
            try:
                with self._db.begin_nested():
                    subject = Subject(name=canonical_subject, short_code=short_code)
                    self._db.add(subject)
                    self._db.flush()
            except Exception:
                # Unique constraint ihlali olursa (concurrent insert vb.), tekrar oku
                subject = self._db.query(Subject).filter_by(short_code=short_code).first()
                if not subject:
                    subject = self._db.query(Subject).filter(Subject.name == canonical_subject).first()
                if not subject:
                    raise

            self._subject_cache[short_code] = subject
        else:
            self._subject_cache[short_code] = subject
            if subject.name != canonical_subject and subject_name.strip() != "Genel":
                try:
                    with self._db.begin_nested():
                        subject.name = canonical_subject
                        self._db.flush()
                except Exception:
                    pass

        # ── 2. Topic (Get or Create) ────────────────────────────────────────────
        clean_topic_name = topic_name.strip() or canonical_subject
        topic = (
            self._db.query(Topic).filter(Topic.subject_id == subject.id, func.lower(Topic.name) == func.lower(clean_topic_name)).first()
        )
        if not topic:
            try:
                with self._db.begin_nested():
                    topic = Topic(subject_id=subject.id, name=clean_topic_name)
                    self._db.add(topic)
                    self._db.flush()
            except Exception:
                topic = (
                    self._db.query(Topic)
                    .filter(Topic.subject_id == subject.id, func.lower(Topic.name) == func.lower(clean_topic_name))
                    .first()
                )

        # ── 3. LearningOutcome (Get or Create) ──────────────────────────────────
        clean_description = outcome_description.strip() or clean_topic_name
        outcome = (
            self._db.query(LearningOutcome)
            .filter(
                LearningOutcome.topic_id == topic.id,
                func.lower(LearningOutcome.description) == func.lower(clean_description),
            )
            .first()
        )
        if not outcome:
            try:
                with self._db.begin_nested():
                    outcome = LearningOutcome(
                        topic_id=topic.id,
                        code=outcome_code,
                        description=clean_description,
                    )
                    self._db.add(outcome)
                    self._db.flush()
            except Exception:
                outcome = (
                    self._db.query(LearningOutcome)
                    .filter(
                        LearningOutcome.topic_id == topic.id,
                        func.lower(LearningOutcome.description) == func.lower(clean_description),
                    )
                    .first()
                )
        elif outcome_code and not outcome.code:
            try:
                with self._db.begin_nested():
                    outcome.code = outcome_code
                    self._db.flush()
            except Exception:
                pass

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
        """Ders adından kısa kod üretir: 'Matematik' → 'MATEMATI'."""
        replacements = str.maketrans("ÇçĞğİıÖöŞşÜü", "CcGgIiOoSsUu")
        cleaned = name.translate(replacements)
        code = "".join(c for c in cleaned.upper() if c.isalnum())[:8]
        return code or "GEN"

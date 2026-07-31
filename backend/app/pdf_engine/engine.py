"""
PDF Engine — ana orkestratör.

Sorumluluk (mimari-sablon.md §4.1):
  detect → extract → normalize → validate zincirini yönetir.
  Her adımın sonucu bir sonraki adıma girdi olur.
  Herhangi bir aşamada kritik hata oluşursa işlem durur ve
  EngineResult.status ile neden raporlanır.

Kullanım (upload_service.py tarafından çağrılır):
    from pathlib import Path
    from app.pdf_engine.engine import PDFEngine

    engine = PDFEngine()
    result = engine.process(Path("/uploads/raw/<uuid>/rapor.pdf"))

    if result.status == EngineResultStatus.OK:
        # result.normalized_data → DB'ye yaz
        ...
    elif result.status == EngineResultStatus.NEEDS_REVIEW:
        # result → review_queue'ya ekle
        ...
    else:  # FAILED
        # Kritik hata; raw_files.status = "NEEDS_REVIEW"
        ...

Bu modül hiçbir DB çağrısı yapmaz.
DB yazma sorumluluğu upload_service.py'dedir (katman ayrımı — P4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.pdf_engine.detector import FormatDetector
from app.pdf_engine.ocr_fallback import is_image_based_pdf
from app.pdf_engine.parsers.base_parser import BasePDFParser
from app.pdf_engine.validator import ValidationError, validate_result_counts

logger = logging.getLogger(__name__)


# ── Durum sabitleri ───────────────────────────────────────────────────────────


class EngineResultStatus:
    """EngineResult.status için sabit değerler."""

    OK = "OK"  # Tüm adımlar başarılı, DB'ye yazılabilir
    NEEDS_REVIEW = "NEEDS_REVIEW"  # İnsan onayı gerekiyor
    FAILED = "FAILED"  # Kritik hata, işlem tamamlanamadı


class ReviewReason:
    """review_queue.reason için sabit değerler."""

    IMAGE_BASED_PDF = "IMAGE_BASED_PDF"
    UNKNOWN_FORMAT = "UNKNOWN_FORMAT"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    NORMALIZATION_FAILED = "NORMALIZATION_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


# ── Sonuç veri yapısı ─────────────────────────────────────────────────────────


@dataclass
class EngineResult:
    """PDF işleme zincirinin bütünleşik sonucu.

    upload_service.py bu nesneyi tüketir ve uygun DB işlemlerini yapar.

    Attributes:
        status:            "OK" | "NEEDS_REVIEW" | "FAILED"
        parser_name:       Kullanılan parser'ın adı veya "UNKNOWN_FORMAT".
        confidence:        Detector'ın format eşleşme güveni (0.0 – 1.0).
        raw_data:          extract() çıktısı — raw_extractions.raw_json'a yazılır.
                           FAILED durumunda boş dict olabilir.
        normalized_data:   normalize() çıktısı — DB'ye yazılacak veri.
                           OK değilse None olabilir.
        validation_errors: Her subject_result satırı için validator hataları.
        warnings:          Tüm aşamalardan biriken engelleyici olmayan uyarılar.
        review_reason:     NEEDS_REVIEW veya FAILED durumunda neden (ReviewReason).
        review_detail:     İnsan tarafından okunabilir hata detayı.
    """

    status: str
    parser_name: str
    confidence: float
    raw_data: dict[str, Any] = field(default_factory=dict)
    normalized_data: dict[str, Any] | None = None
    validation_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    review_reason: str | None = None
    review_detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == EngineResultStatus.OK

    @property
    def needs_review(self) -> bool:
        return self.status == EngineResultStatus.NEEDS_REVIEW

    @property
    def failed(self) -> bool:
        return self.status == EngineResultStatus.FAILED

    def __repr__(self) -> str:
        return (
            f"<EngineResult status={self.status!r} "
            f"parser={self.parser_name!r} "
            f"warnings={len(self.warnings)} "
            f"val_errors={len(self.validation_errors)}>"
        )


# ── Ana Engine Sınıfı ─────────────────────────────────────────────────────────


class PDFEngine:
    """PDF işleme zincirini orkestre eden ana sınıf.

    detect → extract → normalize → validate

    Her adım izole hata yönetimiyle sarılmıştır:
    - Bir adım başarısız olursa sonraki adımlar çalıştırılmaz.
    - Hata detayı EngineResult'a yazılır.
    - Sessiz hata yoktur (P3).
    """

    def __init__(
        self,
        detector: FormatDetector | None = None,
    ) -> None:
        """
        Args:
            detector: Test bağlamında mock detector enjekte etmek için.
                      None ise varsayılan FormatDetector kullanılır.
        """
        self._detector = detector or FormatDetector()

    # ── Genel API ─────────────────────────────────────────────────────────────

    def process(self, pdf_path: Path) -> EngineResult:
        """PDF'i uçtan uca işler: detect → extract → normalize → validate.

        Bu metodun kendisi hiçbir zaman exception fırlatmaz.
        Tüm hatalar EngineResult içinde raporlanır.

        Args:
            pdf_path: İşlenecek PDF dosyasının pathlib.Path nesnesi.

        Returns:
            EngineResult — status alanı işlem sonucunu özetler.
        """
        logger.info("PDF Engine başlatıldı: %s", pdf_path.name)

        # ── Adım 0: İmaj tabanlı PDF (tarayıcı) kontrolü ──────────────────
        if is_image_based_pdf(pdf_path):
            logger.warning("Resim tabanlı PDF tespit edildi: %s", pdf_path.name)
            return EngineResult(
                status=EngineResultStatus.NEEDS_REVIEW,
                parser_name="UNKNOWN_FORMAT",
                confidence=0.0,
                raw_data={},
                warnings=["PDF salt resim içeriyor, metin katmanı bulunamadı."],
                review_reason=ReviewReason.IMAGE_BASED_PDF,
                review_detail=(
                    "PDF içinde yeterli metin bulunamadı. "
                    "Dosya muhtemelen tarayıcıdan (scanner) resim olarak aktarılmış. "
                    "Bu formattaki dosyalar otomatik işlenememektedir."
                ),
            )

        # ── Adım 1: Format tespiti ─────────────────────────────────────────
        detection = self._detector.detect(pdf_path)

        if detection.is_unknown:
            logger.warning("Format tanınamadı: %s", pdf_path.name)
            return EngineResult(
                status=EngineResultStatus.NEEDS_REVIEW,
                parser_name=detection.parser_name,  # "UNKNOWN_FORMAT"
                confidence=0.0,
                raw_data={},
                warnings=detection.warnings,
                review_reason=ReviewReason.UNKNOWN_FORMAT,
                review_detail=(
                    f"PDF formatı tanınamadı. "
                    f"Kayıtlı parser sayısı: {len(self._detector._parsers)}. "
                    "Yeni format desteği için parser eklenmelidir."
                ),
            )

        parser: BasePDFParser = detection.parser  # type: ignore[assignment]
        accumulated_warnings: list[str] = list(detection.warnings)

        # ── Adım 2: Ham veri çekimi (extract) ─────────────────────────────
        raw_data: dict[str, Any] = {}
        try:
            raw_data = parser.extract(pdf_path)
            accumulated_warnings.extend(raw_data.get("warnings", []))
            accumulated_warnings.extend(raw_data.get("errors", []))

            logger.info(
                "extract() tamamlandı: parser=%s öğrenci=%d",
                parser.parser_name,
                len(raw_data.get("raw_students", [])),
            )
        except Exception as exc:  # noqa: BLE001
            detail = f"extract() başarısız — {type(exc).__name__}: {exc}"
            logger.error(detail, exc_info=True)
            return EngineResult(
                status=EngineResultStatus.FAILED,
                parser_name=detection.parser_name,
                confidence=detection.confidence,
                raw_data=raw_data,
                warnings=accumulated_warnings,
                review_reason=ReviewReason.EXTRACTION_FAILED,
                review_detail=detail,
            )

        # ── Adım 3: Normalleştirme (normalize) ────────────────────────────
        normalized_data: dict[str, Any] | None = None
        try:
            normalized_data = parser.normalize(raw_data)
            accumulated_warnings.extend(normalized_data.get("warnings", []))

            logger.info(
                "normalize() tamamlandı: öğrenci=%d",
                len(normalized_data.get("student_results", [])),
            )
        except Exception as exc:  # noqa: BLE001
            detail = f"normalize() başarısız — {type(exc).__name__}: {exc}"
            logger.error(detail, exc_info=True)
            return EngineResult(
                status=EngineResultStatus.NEEDS_REVIEW,
                parser_name=detection.parser_name,
                confidence=detection.confidence,
                raw_data=raw_data,
                normalized_data=None,
                warnings=accumulated_warnings,
                review_reason=ReviewReason.NORMALIZATION_FAILED,
                review_detail=detail,
            )

        # ── Adım 4: Doğrulama (validate) ──────────────────────────────────
        validation_errors = self._validate_normalized(normalized_data)

        if validation_errors:
            logger.warning(
                "Doğrulama hataları bulundu: %d hata — NEEDS_REVIEW",
                len(validation_errors),
            )
            return EngineResult(
                status=EngineResultStatus.NEEDS_REVIEW,
                parser_name=detection.parser_name,
                confidence=detection.confidence,
                raw_data=raw_data,
                normalized_data=normalized_data,
                validation_errors=validation_errors,
                warnings=accumulated_warnings,
                review_reason=ReviewReason.VALIDATION_FAILED,
                review_detail=(f"{len(validation_errors)} doğrulama hatası bulundu. İnsan incelemesi gerekiyor."),
            )

        # ── Tüm adımlar başarılı ──────────────────────────────────────────
        logger.info(
            "PDF Engine tamamlandı — OK: parser=%s",
            parser.parser_name,
        )
        return EngineResult(
            status=EngineResultStatus.OK,
            parser_name=detection.parser_name,
            confidence=detection.confidence,
            raw_data=raw_data,
            normalized_data=normalized_data,
            validation_errors=[],
            warnings=accumulated_warnings,
        )

    # ── Özel: Toplu doğrulama ─────────────────────────────────────────────────

    def _validate_normalized(
        self,
        normalized_data: dict[str, Any],
    ) -> list[str]:
        """Normalize edilmiş tüm öğrenci-kazanım satırlarını doğrular.

        validator.validate_result_counts() her satır için çağrılır.
        Fail-fast değildir: hatalı satırlar raporlanır, kontrol devam eder.

        Args:
            normalized_data: normalize() çıktısı.

        Returns:
            Hata mesajları listesi. Boş liste = tüm satırlar geçerli.
        """
        errors: list[str] = []
        students = normalized_data.get("student_results", [])

        for student in students:
            full_name = student.get("full_name", "?")
            subject_results = student.get("subject_results", [])

            for result in subject_results:
                measured = result.get("measured", True)
                subject = result.get("subject_name", "?")
                topic = result.get("outcome_description", "")[:40]

                # measured=False olan satırlar R1 (sayı tutarlılığı) kontrolünden muaf
                # ama R2 (negatif yok), R3 (toplam > 0), R4 (tip), R5 (zorunlu alan)
                # hâlâ uygulanır — validator.py §ADR-004.
                #
                # Ancak: TYT formatında blank hesaplama (Soru-D-Y) bazen negatif
                # çıkabilir (validator bunu R2 ile yakalar). Parser bunu zaten 0'a
                # sabitlediği için buraya 0 gelecek — sorun yok.
                #
                # Ek istisna: measured=False ve total_questions=0 olan satırlar
                # R3 (total > 0) kontrolünden de muaf tutulur.
                if not measured and result.get("total_questions", 0) == 0:
                    # Hiç soru yok, ölçülmedi — doğrulama atla
                    continue

                try:
                    validate_result_counts(
                        {
                            "correct": result.get("correct", 0),
                            "wrong": result.get("wrong", 0),
                            "blank": result.get("blank", 0),
                            "total_expected": result.get("total_questions", 0),
                        },
                        measured=measured,
                    )
                except ValidationError as exc:
                    errors.append(f"Öğrenci '{full_name}' | Ders '{subject}' | Kazanım '{topic}': {exc.message}")

        return errors

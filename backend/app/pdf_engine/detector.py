"""
PDF format tespit modülü.

Sorumluluk (mimari-sablon.md §4.1):
  Yüklenen PDF'e hangi parser'ın uygulanacağını belirler.
  Kayıtlı parser'ları sırayla dener; ilk can_handle() == True döndüreni seçer.
  Hiçbiri eşleşmezse UNKNOWN_FORMAT sonucu döner — bu durum engine.py
  tarafından review_queue'ya "UNKNOWN_FORMAT" olarak yönlendirilir.

Kullanım:
    from app.pdf_engine.detector import FormatDetector, DetectionResult

    detector = FormatDetector()
    result   = detector.detect(Path("rapor.pdf"))

    if result.matched:
        raw = result.parser.extract(pdf_path)
    else:
        # review_queue'ya düşür
        ...

Tasarım notları:
  - can_handle() exception fırlatmamalıdır (base_parser.py sözleşmesi).
    Yine de savunmacı bir try/except ile sarılır; hatalı parser diğerlerini
    engellemez.
  - confidence: Faz 0'da binary (1.0 / 0.0). İleride her parser'ın
    kendi güven skorunu döndürmesi için genişletilebilir.
  - Bu modül hiçbir DB çağrısı yapmaz; saf dosya okuma katmanıdır.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.pdf_engine.parsers import REGISTERED_PARSERS
from app.pdf_engine.parsers.base_parser import BasePDFParser

logger = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────────────

UNKNOWN_FORMAT = "UNKNOWN_FORMAT"


# ── Veri Yapısı ───────────────────────────────────────────────────────────────


@dataclass
class DetectionResult:
    """Format tespit sonucu.

    Attributes:
        matched:     En az bir parser eşleşti mi?
        parser:      Eşleşen parser örneği (None = tanınamadı).
        parser_name: Eşleşen parser'ın adı veya "UNKNOWN_FORMAT".
        confidence:  Eşleşme güveni (0.0 – 1.0).
                     Faz 0'da binary: 1.0 = eşleşti, 0.0 = eşleşmedi.
        warnings:    Tespit sırasında oluşan engelleyici olmayan uyarılar.
    """

    matched: bool
    parser: BasePDFParser | None
    parser_name: str
    confidence: float
    warnings: list[str] = field(default_factory=list)

    @property
    def is_unknown(self) -> bool:
        """Format tanınamadı mı?"""
        return not self.matched


# ── Ana Sınıf ─────────────────────────────────────────────────────────────────


class FormatDetector:
    """PDF formatını tespit eden sınıf.

    REGISTERED_PARSERS listesindeki parser'ları öncelik sırasıyla dener.
    Yeni parser eklemek için parsers/__init__.py listesini güncelle;
    bu sınıfa dokunma (P1 — modülerlik).
    """

    def __init__(
        self,
        parsers: list[BasePDFParser] | None = None,
    ) -> None:
        """
        Args:
            parsers: Test bağlamında mock parser enjekte etmek için kullanılır.
                     None ise REGISTERED_PARSERS kullanılır.
        """
        self._parsers = parsers if parsers is not None else REGISTERED_PARSERS

    def detect(self, pdf_path: Path) -> DetectionResult:
        """Verilen PDF dosyasının formatını tespit eder.

        Algoritma:
          1. Kayıtlı parser'lar öncelik sırasıyla denenir.
          2. İlk can_handle() == True döndüren parser seçilir.
          3. Hiçbiri eşleşmezse UNKNOWN_FORMAT döner.

        Hiçbir zaman exception fırlatmaz — hatalı parser'lar uyarı
        olarak raporlanır, diğerleri denenmaya devam eder.

        Args:
            pdf_path: İşlenecek PDF dosyasının yolu.

        Returns:
            DetectionResult — matched=True veya False.
        """
        warnings: list[str] = []

        if not self._parsers:
            logger.warning("Kayıtlı parser yok; UNKNOWN_FORMAT dönülüyor.")
            return DetectionResult(
                matched=False,
                parser=None,
                parser_name=UNKNOWN_FORMAT,
                confidence=0.0,
                warnings=["Kayıtlı parser listesi boş."],
            )

        for parser in self._parsers:
            try:
                if parser.can_handle(pdf_path):
                    logger.info(
                        "Format eşleşti: pdf=%s parser=%s",
                        pdf_path.name,
                        parser.parser_name,
                    )
                    return DetectionResult(
                        matched=True,
                        parser=parser,
                        parser_name=parser.parser_name,
                        confidence=1.0,
                        warnings=warnings,
                    )
            except Exception as exc:  # noqa: BLE001
                msg = f"Parser '{parser.parser_name}' can_handle() sırasında beklenmedik hata (atlanıyor): {exc}"
                logger.warning(msg)
                warnings.append(msg)

        # Hiçbir parser eşleşmedi
        logger.warning(
            "Format tanınamadı: pdf=%s — %d parser denendi",
            pdf_path.name,
            len(self._parsers),
        )
        return DetectionResult(
            matched=False,
            parser=None,
            parser_name=UNKNOWN_FORMAT,
            confidence=0.0,
            warnings=warnings,
        )

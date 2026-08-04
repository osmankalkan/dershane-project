"""
Parser paketi — kayıtlı parser'ların merkezi listesi.

Yeni bir format desteği eklemek için tek yapılacak iş:
  1. parsers/ altına yeni bir dosya oluştur (parser_xxx.py)
  2. Sınıfı buraya import et
  3. REGISTERED_PARSERS listesine ekle

Başka hiçbir dosyaya dokunulmaz (mimari-sablon.md §4, P1).

Sıra önemlidir: daha spesifik (kısıtlayıcı) can_handle() kontrolüne
sahip parser'lar listenin başına gelmelidir. detector.py ilk True
döndüren parser'ı seçer; yanlış pozitif riskini azaltmak için sıra
dikkatlice belirlenmeli.
"""

from __future__ import annotations

from app.pdf_engine.parsers.base_parser import BasePDFParser
from app.pdf_engine.parsers.parser_lgs_format import ParserLGSFormat
from app.pdf_engine.parsers.parser_tyt_format import ParserTYTFormat

# ── Kayıtlı Parser Listesi ────────────────────────────────────────────────────
#
# Her parser bir kez örneklenir (singleton-like); can_handle() state
# taşımadığı için bu güvenlidir. İleride DI container entegrasyonu
# gerekirse burası değiştirilir.

REGISTERED_PARSERS: list[BasePDFParser] = [
    ParserLGSFormat(),
    ParserTYTFormat(),
]

__all__ = ["REGISTERED_PARSERS", "BasePDFParser"]

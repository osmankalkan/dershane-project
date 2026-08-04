"""
Parser paketi.

Bu paket, desteklenen sınav formatları için ayrıştırıcı (parser) sınıflarını içerir.
Factory pattern kullanımıyla birlikte REGISTERED_PARSERS mantığı iptal edilmiştir.
"""

from app.pdf_engine.parsers.base_parser import BaseExamParser
from app.pdf_engine.parsers.parser_lgs_format import LGSParser
from app.pdf_engine.parsers.parser_tyt_format import TYTParser

__all__ = ["BaseExamParser", "LGSParser", "TYTParser"]

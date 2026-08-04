from pathlib import Path

import pdfplumber

from app.pdf_engine.parsers.base_parser import BaseExamParser
from app.pdf_engine.parsers.parser_lgs_format import LGSParser
from app.pdf_engine.parsers.parser_tyt_format import TYTParser


class ParserFactory:
    """
    Sisteme yüklenen PDF dosyasını analiz ederek hangi formata (TYT, LGS vb.)
    uygun olduğuna karar verir ve ilgili parser nesnesini döner.
    """

    @staticmethod
    def create_parser(pdf_path: Path, format_hint: str = None) -> BaseExamParser:
        """
        PDF dosyasını alır, içeriğine bakarak doğru parser sınıfını başlatır.

        Args:
            pdf_path: Yüklenecek PDF dosyasının yolu.
            format_hint: Kullanıcı arayüzünden (endpoint'ten) gelen ipucu (opsiyonel).

        Returns:
            BaseExamParser nesnesi (ör. TYTParser veya LGSParser)

        Raises:
            ValueError: Format belirlenemezse.
        """

        # Eğer ipucu gelmişse direkt olarak ilgili parser'ı döndür
        if format_hint:
            format_hint = format_hint.upper()
            if "TYT" in format_hint:
                return TYTParser(pdf_path)
            elif "LGS" in format_hint:
                return LGSParser(pdf_path)

        # İpucu yoksa PDF'in içine bakarak analiz yap
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    raise ValueError("PDF dosyası boş veya okunabilir bir sayfa içermiyor.")

                first_page_text = pdf.pages[0].extract_text() or ""
                first_page_text = first_page_text.upper()

                # LGS işaretçileri
                if "LGS" in first_page_text or "8.SINIF" in first_page_text or "MADALYON" in first_page_text:
                    return LGSParser(pdf_path)

                # TYT işaretçileri
                if "SINAV SONUÇ BELGESİ" in first_page_text:
                    return TYTParser(pdf_path)

                # Hiçbirine uymuyorsa hata fırlat
                raise ValueError("PDF formatı tanımlanamadı (LGS veya TYT işaretçileri bulunamadı).")

        except Exception as e:
            raise ValueError(f"PDF analiz edilemedi: {e}")

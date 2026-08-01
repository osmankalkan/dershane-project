"""
Resim Tabanlı (Image-Based) PDF Kontrolü.

Faz 0:
Sistemi yormamak adına OCR (Tesseract) çalıştırılmamaktadır (Kullanıcı kararı).
Bunun yerine yüklenen PDF'in salt resim (metin katmanı olmayan tarayıcı çıktısı)
olup olmadığı basitçe kontrol edilir.

Eğer PDF'ten yeterli metin çıkarılamıyorsa dosyanın "IMAGE_BASED_PDF" olarak
doğrudan NEEDS_REVIEW kuyruğuna düşmesi sağlanır.
"""

import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def check_pdf_accessibility(pdf_path: Path, text_length_threshold: int = 50) -> str:
    """PDF'in fiziksel durumunu ve metin içerip içermediğini kontrol eder.

    Returns:
        str: "OK" (Sorun yok), "IMAGE_BASED" (Tarayıcı), "CORRUPTED" (Fiziksel bozukluk)
    """
    total_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_check = min(3, len(pdf.pages))

            for i in range(pages_to_check):
                text = pdf.pages[i].extract_text()
                if text:
                    total_text += text.strip()

                if len(total_text) > text_length_threshold:
                    return "OK"

        return "IMAGE_BASED" if len(total_text) < text_length_threshold else "OK"
    except Exception as exc:
        logger.warning(f"PDF bozuk veya açılamıyor (check_pdf_accessibility): {exc}")
        return "CORRUPTED"

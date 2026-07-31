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


def is_image_based_pdf(pdf_path: Path, text_length_threshold: int = 50) -> bool:
    """PDF'in metin katmanı içerip içermediğini kontrol eder.

    İlk 3 sayfayı kontrol ederek toplam çıkarılan metin karakter sayısının
    threshold'un altında kalıp kalmadığına bakar. (Örn: Boş PDF veya sadece resim).

    Args:
        pdf_path: Kontrol edilecek PDF'in yolu.
        text_length_threshold: Toplam metin karakteri için minimum sınır.

    Returns:
        bool: True ise dosya yüksek ihtimalle salt resim veya OCR gerektiriyor.
    """
    total_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Tüm PDF'i okumak yerine sadece ilk 3 sayfaya bakmak (hız için)
            pages_to_check = min(3, len(pdf.pages))

            for i in range(pages_to_check):
                text = pdf.pages[i].extract_text()
                if text:
                    total_text += text.strip()

                # Zaten yeteri kadar metin bulduysak, resmi olmadığını anlarız
                if len(total_text) > text_length_threshold:
                    return False

        # Döngü bittiğinde hala metin çok azsa veya yoksa
        return len(total_text) < text_length_threshold
    except Exception as exc:
        logger.warning(f"PDF okunurken hata oluştu (is_image_based_pdf): {exc}")
        # PDF bozuk bile olsa "metin yok" olarak davran ki engine hata dönsün
        return True

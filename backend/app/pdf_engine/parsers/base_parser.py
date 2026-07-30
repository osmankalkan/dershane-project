"""
PDF parser plugin sisteminin sözleşme katmanı.

Her yeni yayınevi/format desteği bu modüldeki soyut sınıfı uygulayarak eklenir.
Mevcut parser'lara hiçbir zaman dokunulmaz — yeni format = yeni dosya (mimari-sablon.md §4, P1).

Hiyerarşi:
    BasePDFParser          ← bu dosya (sözleşme)
        └── ParserYayineviA  ← parser_yayinevi_a.py
        └── ParserYayineviB  ← parser_yayinevi_b.py  (ileride eklenecek)
        └── ...

Kullanım akışı (engine.py tarafından orchestrate edilir):
    1. detector.py → hangi parser'ın can_handle() döndürdüğü bulunur
    2. parser.extract(pdf_path) → ham veri çekilir
    3. parser.normalize(raw_data) → ortak formata dönüştürülür
    4. validator.py → tutarlılık kontrolü
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BasePDFParser(ABC):
    """Tüm PDF parser'larının uygulamak zorunda olduğu soyut temel sınıf.

    Bu sınıf bir "sözleşme" (contract) tanımlar:
    - Her parser 3 metodu eksiksiz uygulamalıdır.
    - Metodların dönüş tipleri ve anlamları değişmez; sadece içerik formatı parser'a özgüdür.
    - Yeni bir parser eklemek için bu sınıftan türetilmiş yeni bir dosya oluşturmak yeterlidir.

    Önemli kural (P3 — Sessiz hata yok):
    Herhangi bir metod, kesin bir hata durumunda exception fırlatmalıdır.
    Şüpheli / belirsiz durumlarda ise dönüş sözlüğüne uyarı eklenir;
    nihai karar validator.py ve review_queue mekanizmasına bırakılır.
    """

    # ── Alt sınıfların kendilerini tanıtmak için override ettiği sınıf değişkeni ──
    #    Örn. "YAYINEVI_A_V1" — raw_extractions.parser_used alanına kaydedilir.
    parser_name: str = ""

    @abstractmethod
    def can_handle(self, pdf_path: Path) -> bool:
        """Bu parser, verilen PDF dosyasını işleyebilir mi?

        Format Detector (detector.py) tarafından çağrılır. Kayıtlı tüm
        parser'lar üzerinde sırayla denenir; ilk True döndüren parser seçilir.

        Uygulama ipuçları:
        - PDF'in ilk N sayfasındaki anahtar kelimeleri kontrol et
          (örn. yayınevi adı, rapor başlığı, sayfa düzeni).
        - Tablo yapısını veya sütun başlıklarını doğrula.
        - Yanlış pozitif riskini azaltmak için birden fazla sinyal kullan.
        - Bu metod hiçbir zaman exception fırlatmamalıdır; tanımlanamayan
          bir formatta sessizce False dönmelidir.

        Args:
            pdf_path: İşlenecek PDF dosyasının yolu (pathlib.Path).
                      Dosyanın var olduğu çağrı öncesinde doğrulanmıştır.

        Returns:
            True  — Bu parser dosyayı işleyebilir.
            False — Bu parser dosyayı tanımıyor; bir sonraki parser denenir.
        """
        ...

    @abstractmethod
    def extract(self, pdf_path: Path) -> dict[str, Any]:
        """PDF dosyasından ham veriyi çeker; normalleştirme yapmaz.

        Amaç: PDF'e özgü yapıyı (tablo, metin, koordinat) olduğu gibi
        Python sözlüğüne aktarmaktır. Bu çıktı doğrudan
        raw_extractions.raw_json alanına kaydedilir (ADR-003).

        Normalleştirme bu metodun sorumluluğunda DEĞİLDİR.
        Kısmi başarılar (bazı sayfalar okunabildi, bazıları okunamadı)
        warnings listesiyle raporlanmalıdır; exception fırlatılmaz.

        Dönüş sözlüğünde bulunması beklenen anahtarlar
        (normalize() bu yapıyı tüketir):
        {
            "raw_students": [...],   # Parser'a özgü öğrenci veri blokları
            "raw_exam_info": {...},  # Sınav adı, tarihi vb. (format bağımlı)
            "warnings": [...],       # Engelleyici olmayan sorunlar (str listesi)
            "errors": [...],         # Ciddi ama kısmi ilerleyişe izin veren sorunlar
        }

        Engelleyici hata durumlarında (dosya okunamıyor, şifre korumalı vb.)
        exception fırlatılır ve upload_service bu durumu review_queue'ya "EXTRACTION_FAILED"
        olarak ekler.

        Args:
            pdf_path: İşlenecek PDF dosyasının yolu (pathlib.Path).

        Returns:
            Parser'a özgü ham veri sözlüğü. Yapı parser'dan parser'a farklılık
            gösterebilir; normalize() ile standart forma dönüştürülür.

        Raises:
            ExtractionError: PDF dosyası hiç okunamıyorsa (şifreli, bozuk vb.).
        """
        ...

    @abstractmethod
    def normalize(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Ham parser çıktısını tüm parser'lar için ortak formata dönüştürür.

        Bu metod extract() çıktısını alır ve validator.py'nin anlayacağı
        standart yapıya çevirir. Böylece validator, engine ve analitik katmanı
        hangi yayınevinden geldiğinden bağımsız, tek bir veri sözleşmesiyle çalışır.

        Beklenen çıktı yapısı (NormalizedExamData sözleşmesi):
        {
            "exam_date":        str,         # ISO 8601: "YYYY-MM-DD"
            "institution_name": str,         # Rapordan okunan kurum adı
            "source_format":    str,         # Örn. "YAYINEVI_A_V1"
            "student_results": [             # Öğrenci başına bir sözlük
                {
                    "student_code":    str,  # Sınav raporu öğrenci ID'si
                    "full_name":       str,
                    "subject_results": [     # Ders başına bir sözlük
                        {
                            "subject_name":       str,
                            "topic_name":         str,
                            "outcome_code":       str | None,
                            "outcome_description":str,
                            "correct":            int,
                            "wrong":              int,
                            "blank":              int,
                            "total_questions":    int,
                            "measured":           bool,
                            # False → bu kazanım sınavda ölçülmedi (ADR-004)
                        },
                        ...
                    ],
                },
                ...
            ],
            "warnings": [...],  # Engelleyici olmayan normalleştirme uyarıları
        }

        Uygulama ipuçları:
        - Alan adı farklılıklarını burada çöz (örn. "ad_soyad" → "full_name").
        - Tarih formatlarını ISO 8601'e dönüştür.
        - measured=False atamasını burada yap; soru sayısı 0 olan kazanımlar
          için measured=False, correct/wrong/blank=0 olarak işaretle.
        - Eksik veya dönüştürülemeyen bir alan için exception yerine
          dönüş sözlüğüne uyarı ekle; nihai karar validator'a bırak.

        Args:
            raw_data: extract() metodunun döndürdüğü ham veri sözlüğü.

        Returns:
            Standart NormalizedExamData formatında sözlük.
            validator.py bu yapıyı tüketir.

        Raises:
            NormalizationError: Temel alanlar (tarih, öğrenci listesi vb.)
                                tamamen eksik veya dönüştürülemez durumdaysa.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} parser_name={self.parser_name!r}>"

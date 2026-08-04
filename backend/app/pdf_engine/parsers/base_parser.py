"""
PDF parser plugin sisteminin sözleşme katmanı.
Strategy / Factory Pattern uygulanmış versiyonudur.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List


class BaseExamParser(ABC):
    """
    Tüm PDF parser'larının uygulamak zorunda olduğu soyut temel sınıf.
    Strategy/Factory Pattern mimarisine uygun olarak, her parser formatı
    için ortak sözleşme sağlar.
    """

    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self._raw_data: Any = None
        self._parsed = False

    @abstractmethod
    def parse(self) -> None:
        """
        PDF dosyasını okuyarak belleğe alır (Caching).
        Bu metot her parser sınıfında uygulanmalı ve extract işlemleri için
        gerekli olan ham veriyi hazırlamalıdır.
        """
        pass

    @abstractmethod
    def extract_student_info(self) -> List[Dict[str, Any]]:
        """
        Öğrenci bilgilerini döndürür.
        Örnek dönüş: [{"student_code": "1234", "full_name": "Ahmet Yılmaz"}, ...]
        """
        pass

    @abstractmethod
    def extract_topics(self) -> List[Dict[str, Any]]:
        """
        Sınavdaki ders/konu dağılımlarını döndürür (Opsiyonel kullanım).
        Örnek dönüş: [{"subject": "Matematik", "topic": "Üslü Sayılar", "questions": 5}, ...]
        """
        pass

    @abstractmethod
    def extract_results(self) -> List[Dict[str, Any]]:
        """
        Öğrencilerin sonuçlarını (doğru, yanlış, boş vb.) döndürür.
        Örnek dönüş: [
            {
                "student_code": "1234",
                "subject_results": [
                    {"subject_name": "Matematik", "outcome_description": "...", "correct": 2, ...}
                ]
            }
        ]
        """
        pass

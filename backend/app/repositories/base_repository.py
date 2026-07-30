"""
Soyut Repository temel sınıfı — veritabanı erişim katmanı sözleşmesi.

Mimari kural (mimari-sablon.md §7, P4):
  - Servis katmanı hangi veritabanını kullandığımızı ASLA bilmez.
  - Tüm DB erişimi bu sınıftan türetilmiş somut sınıflar üzerinden geçer.
  - SQLite → PostgreSQL geçişi (ADR-005) yalnızca engine URL değişikliğidir;
    repository veya servis koduna dokunulmaz.

Generic[T] kullanımı:
  Her somut repository belirli bir model tipiyle çalışır:
    class StudentRepository(SQLAlchemyRepository[Student]):
        ...

Katman sorumlulukları:
  Repository → Sadece DB CRUD + sorgular. İş mantığı YOKTUR.
  Service    → İş kuralları. Repository'yi çağırır; DB'yi doğrudan bilmez.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    """Tüm repository'lerin uygulaması gereken soyut temel sınıf.

    Generic[T] ile belirli bir SQLAlchemy modeli için tiplendirilir.
    Somut implementasyon SQLAlchemy Session kullansa da,
    ileride başka bir storage katmanı (örn. in-memory test double) takılabilir.
    """

    @abstractmethod
    def get_by_id(self, entity_id: uuid.UUID) -> T | None:
        """Birincil anahtar ile tek kayıt getirir.

        Args:
            entity_id: Aranacak UUID.

        Returns:
            Bulunan model örneği veya None.
        """
        ...

    @abstractmethod
    def list_all(self) -> list[T]:
        """Tablodaki tüm kayıtları döndürür.

        Büyük veri setleri için ileride sayfalama (pagination) parametreleri
        eklenmeli; şimdilik Faz 0 kapsamı için tümünü getirir.

        Returns:
            Model örneklerinin listesi (boş olabilir).
        """
        ...

    @abstractmethod
    def create(self, entity: T) -> T:
        """Yeni bir kayıt ekler ve kaydedilmiş örneği döndürür.

        Args:
            entity: Eklenecek model örneği (id alanı UUID4 ile dolu olmalı).

        Returns:
            DB'ye yazıldıktan sonra refresh edilmiş model örneği.
        """
        ...

    @abstractmethod
    def update(self, entity: T) -> T:
        """Mevcut bir kaydı günceller.

        Entity'nin id alanı DB'de var olan bir kaydı göstermelidir.

        Args:
            entity: Güncellenmiş alanları içeren model örneği.

        Returns:
            DB'den yeniden okunan (refresh) güncel model örneği.
        """
        ...

    @abstractmethod
    def delete(self, entity_id: uuid.UUID) -> bool:
        """Kaydı kalıcı olarak siler.

        Not: raw_files ve raw_extractions tabloları için bu metod
        çağrılmamalıdır (ADR-003 — ham veri asla silinmez).
        Bu kural servis katmanında zorlanır.

        Args:
            entity_id: Silinecek kaydın UUID'si.

        Returns:
            True  — kayıt bulundu ve silindi.
            False — kayıt bulunamadı.
        """
        ...

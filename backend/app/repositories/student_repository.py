"""
SQLAlchemy tabanlı somut repository implementasyonları.

Bu modül AbstractRepository'yi SQLAlchemy Session ile uygular.
Faz 0'da SQLite, Faz 1'de PostgreSQL — her iki durumda da bu kod değişmez.
Sadece engine URL'si (config.py) farklıdır.

Kullanım (servis katmanında):
    from app.repositories.student_repository import StudentRepository

    class StudentService:
        def __init__(self, db: Session) -> None:
            self._repo = StudentRepository(db)

        def get_student(self, student_id: uuid.UUID) -> Student | None:
            return self._repo.get_by_id(student_id)
"""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.models.student import Student
from app.repositories.base_repository import AbstractRepository

T = TypeVar("T")


class SQLAlchemyRepository(AbstractRepository[T], Generic[T]):
    """Generic SQLAlchemy implementasyonu.

    Alt sınıflar yalnızca `model_class` sınıf değişkenini tanımlamalıdır.
    Ortak CRUD otomatik miras alınır; fazladan sorgular alt sınıfta eklenir.
    """

    model_class: type  # Alt sınıf tarafından override edilir

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── AbstractRepository implementasyonları ─────────────────────────────────

    def get_by_id(self, entity_id: uuid.UUID) -> T | None:
        return self._db.get(self.model_class, entity_id)

    def list_all(self) -> list[T]:
        return self._db.query(self.model_class).all()

    def create(self, entity: T) -> T:
        self._db.add(entity)
        self._db.commit()
        self._db.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        self._db.commit()
        self._db.refresh(entity)
        return entity

    def delete(self, entity_id: uuid.UUID) -> bool:
        entity = self.get_by_id(entity_id)
        if entity is None:
            return False
        self._db.delete(entity)
        self._db.commit()
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Somut Repository'ler
# ─────────────────────────────────────────────────────────────────────────────


class StudentRepository(SQLAlchemyRepository[Student]):
    """students tablosu için repository."""

    model_class = Student

    def get_by_code(self, class_id: uuid.UUID, student_code: str) -> Student | None:
        """PDF parser'ın kullandığı öğrenci kodu ile arama.

        PDF raporundaki student_code, bu metod aracılığıyla
        DB'deki öğrenciyle eşleştirilir.
        """
        return (
            self._db.query(Student)
            .filter(
                Student.class_id == class_id,
                Student.student_code == student_code,
            )
            .first()
        )

    def list_by_class(self, class_id: uuid.UUID) -> list[Student]:
        """Belirli bir sınıftaki tüm öğrencileri döndürür."""
        return self._db.query(Student).filter(Student.class_id == class_id).order_by(Student.full_name).all()

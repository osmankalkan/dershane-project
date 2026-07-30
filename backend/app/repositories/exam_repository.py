"""
Exam ve Result repository'leri.
"""

from __future__ import annotations

import uuid

from app.models.exam import Exam
from app.repositories.student_repository import SQLAlchemyRepository


class ExamRepository(SQLAlchemyRepository[Exam]):
    """exams tablosu için repository."""

    model_class = Exam

    def list_by_institution(self, institution_id: uuid.UUID) -> list[Exam]:
        """Bir kuruma ait tüm sınavları tarihe göre sıralı döndürür."""
        return (
            self._db.query(Exam)
            .filter(Exam.institution_id == institution_id)
            .order_by(Exam.exam_date.desc())
            .all()
        )

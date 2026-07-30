"""
Result repository — ana veri tablosu erişimi.
"""

from __future__ import annotations

import uuid

from app.models.result import Result
from app.repositories.student_repository import SQLAlchemyRepository


class ResultRepository(SQLAlchemyRepository[Result]):
    """results tablosu için repository.

    Not: delete() kalıtsal olarak mevcut; ancak analitik verisi
    silinmemeli. Servis katmanı bu kısıtı uygular.
    """

    model_class = Result

    def list_by_student(self, student_id: uuid.UUID) -> list[Result]:
        """Bir öğrencinin tüm sınav sonuçlarını döndürür."""
        return self._db.query(Result).filter(Result.student_id == student_id).all()

    def list_by_exam(self, exam_id: uuid.UUID) -> list[Result]:
        """Bir sınavdaki tüm öğrenci sonuçlarını döndürür."""
        return self._db.query(Result).filter(Result.exam_id == exam_id).all()

    def get_by_student_exam_outcome(
        self,
        student_id: uuid.UUID,
        exam_id: uuid.UUID,
        learning_outcome_id: uuid.UUID,
    ) -> Result | None:
        """Unique kısıta karşılık gelen tek sonuç kaydını döndürür.

        Duplicate insert kontrolü için kullanılır.
        """
        return (
            self._db.query(Result)
            .filter(
                Result.student_id == student_id,
                Result.exam_id == exam_id,
                Result.learning_outcome_id == learning_outcome_id,
            )
            .first()
        )

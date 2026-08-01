"""
Exam servis katmanı.

Sınav verilerinin (Exam modeli) veritabanından çekildiği yerdir.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.institution import Class


class ExamService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_all_exams(self, limit: int = 100, skip: int = 0) -> list[dict[str, Any]]:
        """Sisteme yüklenen tüm sınavları listeler."""
        exams = self._db.query(Exam).join(Class).order_by(Exam.exam_date.desc()).offset(skip).limit(limit).all()

        return [
            {
                "id": str(e.id),
                "name": e.name,
                "exam_date": e.exam_date.isoformat(),
                "class_name": e.class_.name,
                "class_id": str(e.class_id),
                "institution_id": str(e.class_.institution_id),
                "created_at": e.created_at.isoformat(),
            }
            for e in exams
        ]

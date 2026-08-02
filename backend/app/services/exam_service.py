"""
Exam servis katmanı.

Sınav verilerinin (Exam modeli) veritabanından çekildiği yerdir.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.exam import Exam


class ExamService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_all_exams(self, limit: int = 100, skip: int = 0) -> list[dict[str, Any]]:
        """Sisteme yüklenen tüm sınavları listeler."""
        exams = self._db.query(Exam).order_by(Exam.exam_date.desc()).offset(skip).limit(limit).all()

        return [
            {
                "id": str(e.id),
                "name": e.name,
                "exam_date": e.exam_date.isoformat(),
                "institution_id": str(e.institution_id),
                "created_at": e.created_at.isoformat(),
            }
            for e in exams
        ]

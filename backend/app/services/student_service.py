"""
Student servis katmanı.

Öğrenci verilerinin (Student modeli ve ilişkili Result kayıtları)
veritabanından çekilip iş mantığıyla harmanlandığı yerdir.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.exam import Exam, LearningOutcome, Subject, Topic
from app.models.institution import Class
from app.models.result import Result
from app.models.student import Student


class StudentService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_all_students(self, limit: int = 100, skip: int = 0, class_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
        """Tüm öğrencileri sayfalamalı olarak listeler. class_id verilirse filtreler."""
        # JOIN kullanarak sınıf bilgilerini de alalım (N+1 problemini önleriz)
        query = self._db.query(Student).join(Class)

        if class_id:
            query = query.filter(Student.class_id == class_id)

        students = query.order_by(Student.full_name).offset(skip).limit(limit).all()

        return [
            {
                "id": str(s.id),
                "full_name": s.full_name,
                "student_code": s.student_code,
                "class_name": s.class_.name,
                "class_id": str(s.class_id),
                "institution_id": str(s.class_.institution_id),
            }
            for s in students
        ]

    def get_student_by_id(self, student_id: uuid.UUID) -> dict[str, Any] | None:
        """Belirli bir öğrencinin temel detaylarını getirir."""
        student = self._db.query(Student).filter(Student.id == student_id).first()

        if not student:
            return None

        return {
            "id": str(student.id),
            "full_name": student.full_name,
            "student_code": student.student_code,
            "class_name": student.class_.name,
            "class_id": str(student.class_id),
            "created_at": student.created_at.isoformat(),
        }

    def get_student_results(self, student_id: uuid.UUID) -> list[dict[str, Any]]:
        """Öğrencinin tüm sınav sonuçlarını ders/konu/kazanım hiyerarşisiyle getirir."""
        # İlgili tüm tabloları JOIN ile çekiyoruz ki çoklu sorgu oluşmasın
        results = (
            self._db.query(Result)
            .join(Exam)
            .join(LearningOutcome)
            .join(Topic)
            .join(Subject)
            .filter(Result.student_id == student_id)
            .order_by(Exam.exam_date.desc(), Subject.name, Topic.name)
            .all()
        )

        # Ham veriyi işleyip gruplamak için kullanacağız
        output = []
        for r in results:
            output.append(
                {
                    "result_id": str(r.id),
                    "exam_id": str(r.exam.id),
                    "exam_name": r.exam.name,
                    "exam_date": r.exam.exam_date.isoformat(),
                    "subject_name": r.learning_outcome.topic.subject.name,
                    "topic_name": r.learning_outcome.topic.name,
                    "outcome_description": r.learning_outcome.description,
                    "correct": r.correct,
                    "wrong": r.wrong,
                    "blank": r.blank,
                    "total_questions": r.total_questions,
                    "net": r.net,
                    "success_rate": r.success_rate,
                    "measured": r.measured,
                }
            )

        return output

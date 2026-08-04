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
        """Tüm öğrencileri sayfalamalı olarak listeler. class_id verilirse filtreler. Ortalama net ve sıra hesaplar."""
        from sqlalchemy import case, func

        from app.models.exam import Exam
        from app.models.result import Result

        # Calculate avg_net: LGS format has 3-wrong penalty (1/3), else 0.25
        penalty_expr = case((Exam.source_format.like("%LGS%"), 1.0 / 3.0), else_=0.25)
        total_net_expr = func.sum(Result.correct) - func.sum(Result.wrong * penalty_expr)
        distinct_exams_expr = func.count(func.distinct(Result.exam_id))

        # In SQLite, if count is 0, we shouldn't divide by it. Since we LEFT JOIN, if there are no results, count is 0.
        # But if there are no results, total_net_expr is NULL. So avg_net will be NULL, which is fine.
        avg_net_expr = total_net_expr / func.nullif(distinct_exams_expr, 0)

        query = (
            self._db.query(Student, Class, avg_net_expr.label("avg_net"))
            .join(Class)
            .outerjoin(Result, Student.id == Result.student_id)
            .outerjoin(Exam, Result.exam_id == Exam.id)
        )

        if class_id:
            query = query.filter(Student.class_id == class_id)

        # Group by student to aggregate results
        query = query.group_by(Student.id, Class.id)

        # Order by avg_net descending (NULLS LAST in Postgres, SQLite handles it, we can coalesce to 0)
        query = query.order_by(func.coalesce(avg_net_expr, -999).desc(), Student.full_name)

        rows = query.offset(skip).limit(limit).all()

        output = []
        for index, row in enumerate(rows):
            student, class_obj, avg_net = row
            # If avg_net is None, it means no exams taken yet. Let's make it 0 for UI simplicity, or keep it None.
            # We'll use round(avg_net, 2) if it exists.
            safe_avg_net = round(avg_net, 2) if avg_net is not None else 0.0

            output.append(
                {
                    "id": str(student.id),
                    "full_name": student.full_name or "İsimsiz Öğrenci",
                    "student_code": student.student_code or "",
                    "class_name": class_obj.name if class_obj else "Bilinmeyen Sınıf",
                    "class_id": str(student.class_id),
                    "institution_id": str(class_obj.institution_id),
                    "avg_net": safe_avg_net,
                    "rank": skip + index + 1,  # 1-based rank
                }
            )

        return output

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

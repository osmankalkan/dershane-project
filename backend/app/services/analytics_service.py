"""
Analitik servis katmanı — Faz 8 ve 9.

Öğrenci bazlı ve Kurum bazlı performans raporları, zaman içi trendler
ve en zayıf/güçlü kazanımları hesaplar.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import asc, func
from sqlalchemy.orm import Session

from app.models.exam import Exam, LearningOutcome, Subject, Topic
from app.models.result import Result


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_student_performance_trend(self, student_id: uuid.UUID) -> list[dict[str, Any]]:
        """Öğrencinin girdiği sınavlardaki ders bazlı başarı trendini hesaplar.

        Tarihe göre sıralı olarak, her sınav için öğrencinin derslerdeki
        net ve başarı yüzdesini döndürür. measured=False kayıtlar dışlanır.
        """
        # SQL eşdeğeri:
        # SELECT e.name, e.exam_date, s.name, sum(correct), sum(total_questions)
        # FROM results JOIN exams JOIN learning_outcomes JOIN topics JOIN subjects
        # WHERE student_id = ? AND measured = True
        # GROUP BY e.id, s.id
        # ORDER BY e.exam_date ASC

        query = (
            self._db.query(
                Exam.id.label("exam_id"),
                Exam.name.label("exam_name"),
                Exam.exam_date,
                Subject.name.label("subject_name"),
                func.sum(Result.correct).label("total_correct"),
                func.sum(Result.wrong).label("total_wrong"),
                func.sum(Result.blank).label("total_blank"),
                func.sum(Result.total_questions).label("total_q"),
            )
            .join(Exam, Result.exam_id == Exam.id)
            .join(LearningOutcome, Result.learning_outcome_id == LearningOutcome.id)
            .join(Topic, LearningOutcome.topic_id == Topic.id)
            .join(Subject, Topic.subject_id == Subject.id)
            .filter(Result.student_id == student_id, Result.measured == True)  # noqa: E712
            .group_by(Exam.id, Subject.id)
            .order_by(asc(Exam.exam_date))
        )

        rows = query.all()

        # Sınav bazlı gruplamak (Frontend'de çizgi grafik çizerken kolaylık olsun diye)
        exams_map: dict[uuid.UUID, dict[str, Any]] = {}

        for row in rows:
            if row.exam_id not in exams_map:
                exams_map[row.exam_id] = {
                    "exam_id": str(row.exam_id),
                    "exam_name": row.exam_name,
                    "exam_date": row.exam_date.isoformat(),
                    "subjects": [],
                }

            total_c = row.total_correct or 0
            total_w = row.total_wrong or 0
            total_q = row.total_q or 1  # 0'a bölme hatasına karşı

            # Formül: Net = Doğru - (Yanlış / 4) (Şu an 4 yanlış 1 doğruyu götürür varsayımıyla,
            # ancak biz basitçe TYT standardı olan 0.25 çarpanı kullanıyoruz.
            # Gerçekte sınav tipine göre bu dinamik olmalı, Faz 0 için 0.25 sabitliyoruz).
            net = total_c - (total_w * 0.25)
            success_rate = (total_c / total_q) * 100.0

            exams_map[row.exam_id]["subjects"].append(
                {
                    "subject_name": row.subject_name,
                    "correct": total_c,
                    "wrong": total_w,
                    "blank": row.total_blank,
                    "total_questions": total_q,
                    "net": net,
                    "success_rate": round(success_rate, 2),
                }
            )

        # Sözlüğü listeye çevir (tarihe göre sıralı olduğu için değerleri direkt listeleyebiliriz)
        return list(exams_map.values())

    def get_institution_weak_topics(self, institution_id: uuid.UUID, limit: int = 10) -> list[dict[str, Any]]:
        """Kurum genelinde tüm sınavlardaki başarı oranına göre EN ZAYIF kazanımları döndürür."""
        # SQL:
        # SELECT s.name, lo.description, sum(correct), sum(total_questions)
        # FROM results JOIN exams JOIN learning_outcomes JOIN topics JOIN subjects
        # WHERE exams.institution_id = ? AND measured = True
        # GROUP BY lo.id
        # ORDER BY (sum(correct)/sum(total_questions)) ASC LIMIT 10

        query = (
            self._db.query(
                Subject.name.label("subject_name"),
                Topic.name.label("topic_name"),
                LearningOutcome.description.label("outcome_description"),
                func.sum(Result.correct).label("total_correct"),
                func.sum(Result.total_questions).label("total_q"),
            )
            .join(Exam, Result.exam_id == Exam.id)
            .join(LearningOutcome, Result.learning_outcome_id == LearningOutcome.id)
            .join(Topic, LearningOutcome.topic_id == Topic.id)
            .join(Subject, Topic.subject_id == Subject.id)
            .filter(Exam.institution_id == institution_id, Result.measured == True)  # noqa: E712
            .group_by(LearningOutcome.id, Subject.id, Topic.id)
        )

        rows = query.all()

        results_computed = []
        for row in rows:
            tc = row.total_correct or 0
            tq = row.total_q or 1
            success_rate = (tc / tq) * 100.0

            results_computed.append(
                {
                    "subject_name": row.subject_name,
                    "topic_name": row.topic_name,
                    "outcome_description": row.outcome_description,
                    "total_correct": tc,
                    "total_questions": tq,
                    "success_rate": round(success_rate, 2),
                }
            )

        # success_rate'e göre küçükten büyüğe sırala (En zayıflar en üstte)
        results_computed.sort(key=lambda x: x["success_rate"])

        return results_computed[:limit]

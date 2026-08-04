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
                Exam.source_format,
                Subject.name.label("subject_name"),
                func.sum(Result.correct).label("total_correct"),
                func.sum(Result.wrong).label("total_wrong"),
                func.sum(Result.blank).label("total_blank"),
                func.sum(Result.total_questions).label("total_q"),
            )
            .select_from(Result)
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

            penalty = 0.25
            if row.source_format and "LGS" in row.source_format.upper():
                penalty = 1.0 / 3.0

            net = total_c - (total_w * penalty)
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
            .select_from(Result)
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
                    "subject_name": row.subject_name or "Genel",
                    "topic_name": row.topic_name or "Bilinmeyen Konu",
                    "outcome_description": row.outcome_description or "Bilinmeyen Kazanım",
                    "total_correct": tc,
                    "total_questions": tq,
                    "success_rate": round(success_rate, 2),
                }
            )

        # success_rate'e göre küçükten büyüğe sırala (En zayıflar en üstte)
        results_computed.sort(key=lambda x: x["success_rate"])

        return results_computed[:limit]

    def get_student_ranking(self, student_id: uuid.UUID) -> dict[str, Any]:
        """Öğrencinin kendi sınıfındaki ve kurumundaki genel başarı sıralamasını hesaplar."""
        from app.models.institution import Class
        from app.models.student import Student

        # Öğrencinin sınıf ve kurum ID'sini al
        student = self._db.query(Student).join(Class).filter(Student.id == student_id).first()
        if not student:
            return {"rank_in_class": 0, "total_in_class": 0, "rank_in_institution": 0, "total_in_institution": 0}

        class_id = student.class_id
        institution_id = student.class_.institution_id

        # Kurumdaki tüm öğrencilerin net ortalamasını (ya da toplam netini) hesapla
        # Subquery: Her öğrenci için toplam net (sum(correct) - sum(wrong)*0.25)
        # SQLAlchemy func.sum ile yapalım.
        # Basitlik için sadece sum(correct) kullanabiliriz veya result üzerinden hesaplayabiliriz.
        # Daha doğru bir sıralama için: öğrenci bazlı toplam doğru oranına bakalım.

        # Öğrenci ID'si -> Toplam Doğru Sözlüğü (Kurumdaki herkes için)
        results = (
            self._db.query(Result.student_id, Student.class_id, func.sum(Result.correct).label("total_correct"))
            .select_from(Result)
            .join(Student, Result.student_id == Student.id)
            .join(Class, Student.class_id == Class.id)
            .filter(Class.institution_id == institution_id)
            .group_by(Result.student_id, Student.class_id)
            .all()
        )

        institution_scores = []
        class_scores = []

        for r in results:
            score = r.total_correct or 0
            institution_scores.append({"student_id": r.student_id, "score": score})
            if r.class_id == class_id:
                class_scores.append({"student_id": r.student_id, "score": score})

        # Tüm öğrencilerin (sınava girmeyenlerin de) sayısı
        total_in_inst = self._db.query(Student).join(Class).filter(Class.institution_id == institution_id).count()
        total_in_class = self._db.query(Student).filter(Student.class_id == class_id).count()

        # Sırala (Yüksek skor en üstte)
        institution_scores.sort(key=lambda x: x["score"], reverse=True)
        class_scores.sort(key=lambda x: x["score"], reverse=True)

        # Öğrencinin sırasını bul (Listede yoksa bile son sıradadır varsayımı)
        inst_rank = total_in_inst
        for i, s in enumerate(institution_scores):
            if s["student_id"] == student_id:
                inst_rank = i + 1
                break

        cls_rank = total_in_class
        for i, s in enumerate(class_scores):
            if s["student_id"] == student_id:
                cls_rank = i + 1
                break

        return {
            "rank_in_class": cls_rank,
            "total_in_class": max(total_in_class, 1),
            "rank_in_institution": inst_rank,
            "total_in_institution": max(total_in_inst, 1),
        }

    def get_at_risk_students(self, drop_threshold_percent: float = 15.0) -> list[dict[str, Any]]:
        """Ortalama netine kıyasla son sınavında %drop_threshold_percent ve üzeri düşüş yaşayan öğrencileri getirir."""
        from sqlalchemy.orm import joinedload

        from app.models.student import Student

        # Tüm öğrencileri çek (küçük veriseti için in-memory işlem yapıyoruz, büyük veri için SQL optimize edilmeli)
        students = self._db.query(Student).options(joinedload(Student.class_)).all()
        at_risk = []

        for student in students:
            trends = self.get_student_performance_trend(student.id)
            if len(trends) < 2:
                continue  # Kıyaslamak için en az 2 sınav lazım

            # Genel Ortalama Net (tüm sınavlar)
            total_net = sum(sum(subj["net"] for subj in exam["subjects"]) for exam in trends)
            avg_net = total_net / len(trends)

            # Son sınav neti
            last_exam = trends[-1]
            last_net = sum(subj["net"] for subj in last_exam["subjects"])

            if avg_net <= 0:
                continue

            # Düşüş yüzdesi hesapla
            drop_percent = ((avg_net - last_net) / avg_net) * 100.0

            if drop_percent >= drop_threshold_percent:
                at_risk.append(
                    {
                        "student_id": str(student.id),
                        "full_name": student.full_name or "Bilinmeyen Öğrenci",
                        "class_name": student.class_.name if student.class_ else "Bilinmeyen Sınıf",
                        "avg_net": round(avg_net, 2),
                        "last_net": round(last_net, 2),
                        "drop_percent": round(drop_percent, 1),
                        "last_exam_name": last_exam["exam_name"],
                    }
                )

        # En çok düşüş yaşayandan en aza doğru sırala
        at_risk.sort(key=lambda x: x["drop_percent"], reverse=True)
        return at_risk

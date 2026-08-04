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

    def delete_exam(self, exam_id: Any) -> bool:
        """Belirtilen sınavı, sonuçlarını (Result) ve ilişkili ham dosya (RawFile) kayıtlarını siler."""
        import logging
        from pathlib import Path

        from app.models.raw_file import RawExtraction, ReviewQueue
        from app.models.result import Result

        logger = logging.getLogger(__name__)

        exam = self._db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            return False

        raw_file = exam.raw_file

        # 1. Sınava ait tüm Result kayıtlarını sil
        self._db.query(Result).filter(Result.exam_id == exam.id).delete(synchronize_session=False)

        # 2. Sınav kaydını sil
        self._db.delete(exam)
        self._db.flush()

        # 3. İlişkili RawFile ve fiziki dosyayı temizle
        if raw_file:
            try:
                if raw_file.file_path:
                    p = Path(raw_file.file_path)
                    if p.exists():
                        p.unlink()
                        if p.parent.exists() and not any(p.parent.iterdir()):
                            p.parent.rmdir()
            except Exception as e:
                logger.warning("Fiziksel dosya silinirken hata: %s", e)

            # RawExtraction ve ReviewQueue bağımlılıklarını temizle
            extractions = self._db.query(RawExtraction).filter(RawExtraction.raw_file_id == raw_file.id).all()
            for ext in extractions:
                self._db.query(ReviewQueue).filter(ReviewQueue.raw_extraction_id == ext.id).delete(synchronize_session=False)
                self._db.delete(ext)

            self._db.delete(raw_file)

        self._db.commit()

        # 4. Sınav silindikten sonra hiçbir sonucu kalmayan (orphan) öğrencileri temizle
        from app.models.student import Student

        orphan_students = self._db.query(Student).outerjoin(Result).filter(Result.id.is_(None)).all()
        for student in orphan_students:
            self._db.delete(student)
        self._db.flush()

        # 5. İçi boşalan sınıfları temizle
        from app.models.institution import Class

        orphan_classes = self._db.query(Class).outerjoin(Student).filter(Student.id.is_(None)).all()
        for cls in orphan_classes:
            self._db.delete(cls)

        self._db.commit()

        return True

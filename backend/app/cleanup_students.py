import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.result import Result
from app.models.student import Student


def cleanup_orphaned_students():
    db = SessionLocal()
    orphan_students = db.query(Student).outerjoin(Result).filter(Result.id.is_(None)).all()
    print(f"Found {len(orphan_students)} orphaned students.")
    for s in orphan_students:
        db.delete(s)
    db.commit()
    print("Orphaned students deleted.")


if __name__ == "__main__":
    cleanup_orphaned_students()

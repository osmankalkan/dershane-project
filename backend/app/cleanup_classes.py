import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.institution import Class
from app.models.student import Student


def cleanup_orphaned_classes():
    db = SessionLocal()
    # Find classes that have no students
    orphan_classes = db.query(Class).outerjoin(Student).filter(Student.id.is_(None)).all()
    print(f"Found {len(orphan_classes)} orphaned classes.")
    for c in orphan_classes:
        db.delete(c)
    db.commit()
    print("Orphaned classes deleted.")


if __name__ == "__main__":
    cleanup_orphaned_classes()

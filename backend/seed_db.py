import uuid

from app.core.database import SessionLocal
from app.models.institution import Class, Institution


def seed():
    db = SessionLocal()
    try:
        # Default Institution
        inst_id = uuid.UUID("b9c954c0-b532-4051-b830-639a98aecde1")
        inst = db.query(Institution).filter_by(id=inst_id).first()
        if not inst:
            inst = Institution(id=inst_id, name="Örnek Dershane", slug="ornek-dershane")
            db.add(inst)
            db.flush()
            print(f"Created institution: {inst.name} with ID {inst.id}")

        # Default Class
        class_id = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
        cls = db.query(Class).filter_by(id=class_id).first()
        if not cls:
            cls = Class(id=class_id, institution_id=inst.id, name="12-A", academic_year="2023-2024")
            db.add(cls)
            db.flush()
            print(f"Created class: {cls.name} with ID {cls.id}")

        db.commit()
        print("Database seeded successfully.")
    except Exception as e:
        print(f"Seed error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed()

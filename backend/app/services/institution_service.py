from typing import Any

from sqlalchemy.orm import Session

from app.models.institution import Class


class InstitutionService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_all_classes(self) -> list[dict[str, Any]]:
        classes = self._db.query(Class).order_by(Class.name).all()
        return [
            {
                "id": str(c.id),
                "name": c.name,
                "institution_id": str(c.institution_id),
            }
            for c in classes
        ]

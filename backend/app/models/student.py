"""
Student modeli.

Tablo:
  - students : Bir sınıfa kayıtlı öğrenciler

Not: student_code sınav raporlarındaki öğrenci kimliğidir;
     PDF parser bu kodu kullanarak öğrenciyle eşleştirir.
"""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Student(UUIDMixin, TimestampMixin, Base):
    """students tablosu."""

    __tablename__ = "students"

    __table_args__ = (
        UniqueConstraint(
            "class_id", "student_code",
            name="uq_student_class_code",
        ),
        # student_code NULL olabilir; NULL'lar UNIQUE kısıtını ihlal etmez
        # (PostgreSQL standardı davranışı).
    )

    class_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("classes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    student_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Sınav raporundaki tanımlayıcı; bazı kurumlar kullanmayabilir.

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    class_: Mapped["Class"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="students"
    )
    results: Mapped[list["Result"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="student",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Student id={self.id} name={self.full_name!r} code={self.student_code!r}>"

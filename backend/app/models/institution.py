"""
Institution ve Class modelleri.

Tablolar:
  - institutions  : Eğitim kurumları (multi-tenant kök tablosu)
  - classes       : Kurum içindeki sınıflar ("7-A", "LGS-2025" vb.)

Genişleme notu (mimari-sablon.md §12):
  Yeni kurum eklemek = bu tabloya satır eklemek. Sıfır kod değişikliği.
"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Institution(UUIDMixin, TimestampMixin, Base):
    """institutions tablosu — tüm varlıkların çatı kurumu."""

    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # URL dostu tanımlayıcı; örn. "bilgi-koleji-ankara"

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    classes: Mapped[list["Class"]] = relationship(back_populates="institution", cascade="all, delete-orphan")
    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="institution"
    )
    raw_files: Mapped[list["RawFile"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="institution"
    )
    exams: Mapped[list["Exam"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="institution"
    )

    def __repr__(self) -> str:
        return f"<Institution id={self.id} slug={self.slug!r}>"


class Class(UUIDMixin, TimestampMixin, Base):
    """classes tablosu — bir kuruma ait sınıf/şube."""

    __tablename__ = "classes"

    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "name",
            "academic_year",
            name="uq_class_institution_name_year",
        ),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # Örn. "7-A", "LGS-2025"

    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)
    # Biçim: "2024-2025"

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    institution: Mapped["Institution"] = relationship(back_populates="classes")
    students: Mapped[list["Student"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="class_", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Class id={self.id} name={self.name!r} year={self.academic_year!r}>"

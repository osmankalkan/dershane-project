"""
Sınav hiyerarşisi modelleri.

Tablolar:
  - subjects          : Dersler  (Matematik, Türkçe ...)
  - topics            : Konular  (Rasyonel Sayılar ...)
  - learning_outcomes : Kazanımlar (belirli bir konunun ölçülebilir çıktısı)
  - exams             : Gerçekleştirilen sınav olayları

Veri hiyerarşisi:
  Subject → Topic → LearningOutcome → Result
"""

import uuid
from typing import Optional

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Subject(UUIDMixin, Base):
    """subjects tablosu — üst düzey ders tanımları."""

    __tablename__ = "subjects"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Örn. "Matematik", "Türkçe"

    short_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    # Örn. "MAT", "TRK" — grafik etiketlerinde kullanılır

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    topics: Mapped[list["Topic"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Subject id={self.id} code={self.short_code!r}>"


class Topic(UUIDMixin, Base):
    """topics tablosu — bir derse ait konu başlıkları."""

    __tablename__ = "topics"

    __table_args__ = (
        UniqueConstraint("subject_id", "name", name="uq_topic_subject_name"),
    )

    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("subjects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Örn. "Rasyonel Sayılar", "Paragraf Anlama"

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    subject: Mapped["Subject"] = relationship(back_populates="topics")
    learning_outcomes: Mapped[list["LearningOutcome"]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Topic id={self.id} name={self.name!r}>"


class LearningOutcome(UUIDMixin, Base):
    """learning_outcomes tablosu — bir konunun ölçülebilir kazanımı."""

    __tablename__ = "learning_outcomes"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Resmi MEB müfredat kodu; bazı yayınevleri kullanmayabilir.

    description: Mapped[str] = mapped_column(Text, nullable=False)

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    topic: Mapped["Topic"] = relationship(back_populates="learning_outcomes")
    results: Mapped[list["Result"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="learning_outcome"
    )

    def __repr__(self) -> str:
        return f"<LearningOutcome id={self.id} code={self.code!r}>"


class Exam(UUIDMixin, TimestampMixin, Base):
    """exams tablosu — bir kurumda gerçekleştirilen sınav."""

    __tablename__ = "exams"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    raw_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("raw_files.id", ondelete="SET NULL"),
        nullable=True,
        # Manuel girişlerde kaynak PDF olmayabilir.
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Örn. "TYT Deneme 3", "LGS Deneme 1"

    exam_date: Mapped[Date] = mapped_column(Date, nullable=False)
    source_format: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Hangi parser ürettiğini belirtir; örn. "YAYINEVI_A_V1"

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    institution: Mapped["Institution"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="exams"
    )
    raw_file: Mapped[Optional["RawFile"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="exam"
    )
    results: Mapped[list["Result"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="exam", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Exam id={self.id} name={self.name!r} date={self.exam_date}>"

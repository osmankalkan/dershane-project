"""
Ham veri katmanı modelleri (ADR-003: ham veri asla silinmez).

Tablolar:
  - raw_files      : Yüklenen PDF'lerin kayıt defteri  — HİÇBİR ZAMAN SİLİNMEZ
  - raw_extractions: Parser'ın ham JSON çıktısı        — HİÇBİR ZAMAN SİLİNMEZ
  - review_queue   : İnsan onayı bekleyen kayıtlar

Neden bu kadar katman? (mimari-sablon.md §5.1)
  Parser'da hata bulunursa raw_extractions'a dokunmadan,
  sadece kodu düzeltip eski PDF'leri yeniden işleyebilirsin.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin, UUIDMixin


class RawFileStatus:
    """raw_files.status için sabit değerler."""

    PENDING = "PENDING"
    EXTRACTED = "EXTRACTED"
    PROCESSED = "PROCESSED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"


class RawFile(UUIDMixin, Base):
    """raw_files tablosu.

    Yüklenen her PDF için bir satır oluşturulur.
    Bu tablo HİÇBİR ZAMAN fiziksel olarak temizlenmez (ADR-003).
    Dosya yolu pathlib.Path ile işlenir; burada TEXT olarak saklanır.
    """

    __tablename__ = "raw_files"

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','EXTRACTED','PROCESSED','NEEDS_REVIEW','REJECTED')",
            name="ck_raw_files_status",
        ),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    # Örn. "/uploads/raw/<UUID>/rapor.pdf"
    # Kod içinde pathlib.Path(raw_file.file_path) ile kullanılır (mimari-sablon.md §1.3).

    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Kullanıcının yüklediği orijinal dosya adı (sanitize edilmiş).

    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # SHA-256; aynı PDF'in iki kez yüklenmesini önler.

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RawFileStatus.PENDING
    )

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    institution: Mapped["Institution"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="raw_files"
    )
    uploaded_by_user: Mapped["User"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="uploaded_files",
        foreign_keys=[uploaded_by],
    )
    extractions: Mapped[list["RawExtraction"]] = relationship(
        back_populates="raw_file", cascade="all, delete-orphan"
    )
    exam: Mapped[Optional["Exam"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="raw_file"
    )

    def __repr__(self) -> str:
        return f"<RawFile id={self.id} status={self.status!r} hash={self.file_hash[:8]}...>"


class RawExtraction(UUIDMixin, Base):
    """raw_extractions tablosu.

    Parser'ın ham JSON çıktısı saklanır.
    Bu tablo HİÇBİR ZAMAN fiziksel olarak temizlenmez (ADR-003).
    """

    __tablename__ = "raw_extractions"

    raw_file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("raw_files.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parser_used: Mapped[str] = mapped_column(String(100), nullable=False)
    # Örn. "YAYINEVI_A_V1" — hangi parser ürettiği izlenebilir.

    detected_format: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # Parser'ın normalleştirilmemiş ham çıktısı.
    # SQLite: JSON string olarak saklanır; PostgreSQL: native JSONB.
    # Sorgulama ihtiyacı doğarsa PostgreSQL'e geçişte JSONB'ye migrate edilir.

    confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    # 0.00 – 1.00; detector'ın format eşleşme güveni.

    warnings: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Engelleyici olmayan uyarı mesajları (str listesi).
    # SQLite: JSON array string; PostgreSQL: native ARRAY(Text).

    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    raw_file: Mapped["RawFile"] = relationship(back_populates="extractions")
    review_entries: Mapped[list["ReviewQueue"]] = relationship(
        back_populates="raw_extraction", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RawExtraction id={self.id} parser={self.parser_used!r}>"


class ReviewQueueStatus:
    """review_queue.status için sabit değerler."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReviewQueue(UUIDMixin, TimestampMixin, Base):
    """review_queue tablosu.

    Validator veya detector'ın şüpheli bulduğu kayıtlar buraya düşer.
    İnsan onayı olmadan normalized tablolara veri yazılmaz (P3 prensibi).
    """

    __tablename__ = "review_queue"

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED')",
            name="ck_review_queue_status",
        ),
    )

    raw_extraction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("raw_extractions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    # Örn. "VALIDATION_FAILED", "UNKNOWN_FORMAT", "STUDENT_NOT_FOUND"

    reason_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # İnsan tarafından okunabilir açıklama.

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReviewQueueStatus.PENDING
    )

    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Onay veya red sebebi; rehber öğretmen tarafından doldurulur.

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    raw_extraction: Mapped["RawExtraction"] = relationship(
        back_populates="review_entries"
    )
    resolver: Mapped[Optional["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="resolved_reviews",
        foreign_keys=[resolved_by],
    )

    def __repr__(self) -> str:
        return f"<ReviewQueue id={self.id} reason={self.reason!r} status={self.status!r}>"

"""
User modeli.

Tablo:
  - users : Sisteme giriş yapan kullanıcılar (admin / counselor / viewer)

Güvenlik notu (mimari-sablon.md §10):
  - hashed_password loglara düşmez (PII).
  - role alanı API katmanında RBAC için kullanılır.
"""

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    """users tablosu."""

    __tablename__ = "users"

    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # NULL ise süper-admin; kuruma bağlı değil.

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    # Düz şifre asla saklanmaz; bcrypt hash.

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="counselor",
        # Geçerli değerler: "admin" | "counselor" | "viewer"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── İlişkiler ─────────────────────────────────────────────────────────────
    institution: Mapped[Optional["Institution"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="users"
    )
    uploaded_files: Mapped[list["RawFile"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="uploaded_by_user",
        foreign_keys="RawFile.uploaded_by",
    )
    resolved_reviews: Mapped[list["ReviewQueue"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="resolver",
        foreign_keys="ReviewQueue.resolved_by",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"

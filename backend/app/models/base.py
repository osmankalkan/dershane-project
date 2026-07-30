"""
Tüm SQLAlchemy modellerinin miras aldığı temel sınıf ve ortak mixin'ler.

Kural (mimari-sablon.md §1.3):
  - Tüm ID'ler UUID  (ADR-001)
  - Zaman damgaları  TIMESTAMPTZ (timezone=True)
  - created_at       sunucu tarafında otomatik
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Proje genelinde tek DeclarativeBase."""
    pass


class UUIDMixin:
    """UUID birincil anahtar mixin'i.

    Tüm tablolarda ID tahmin edilemez olsun diye UUID kullanılır (ADR-001).
    Değer Python tarafında üretilir; PostgreSQL'e bağımlılık yoktur.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """created_at mixin'i — sunucu saatini kullanır, değiştirilemez."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

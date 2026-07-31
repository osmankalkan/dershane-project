"""
Veritabanı bağlantısı ve oturum fabrikası.

Bu modül tamamen DB-agnostiktir (ADR-005, P4 prensibi):
  - SQLite bağlantısı    → DATABASE_URL = "sqlite:///./dershane.db"
  - PostgreSQL bağlantısı → DATABASE_URL = "postgresql://..."
  Hangi DB kullanıldığını yalnızca config.py bilir; burası bilmez.

Faz 0 (SQLite) için özel ayar:
  SQLite, aynı anda birden fazla thread'den erişimi kısıtlar.
  FastAPI her isteği ayrı thread'de çalıştırdığından
  `connect_args={"check_same_thread": False}` gereklidir.
  Bu ayar PostgreSQL'e geçildiğinde otomatik olarak atlanır.

Kullanım (FastAPI dependency):
    from app.core.database import get_session
    from sqlalchemy.orm import Session

    def my_endpoint(db: Session = Depends(get_session)):
        ...
"""

from __future__ import annotations

import uuid as _uuid
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.base import Base


def _build_engine():
    """DATABASE_URL'ye göre doğru engine oluşturur."""
    connect_args: dict = {}

    if settings.is_sqlite:
        # SQLite: çok-thread erişime izin ver (FastAPI için zorunlu)
        connect_args["check_same_thread"] = False

    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        # Faz 0: echo=True → SQL sorgularını terminale yaz (debug kolaylığı)
        # Faz 1'de DEBUG=False yapılınca otomatik kapanır.
        echo=settings.DEBUG,
    )

    if settings.is_sqlite:
        # SQLite'da foreign key kısıtlamalarını etkinleştir
        # (varsayılan olarak kapalıdır — her bağlantıda ayrıca açılmalı)
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Uygulama genelinde tek engine örneği
engine = _build_engine()

# Session fabrikası — her istek için yeni bir oturum açar
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Faz 0: Sistem kullanıcısı için sabit UUID ────────────────────────────────
# Auth aktif olmadığında (ADR-007) yükleme işlemlerinde uploaded_by FK'si
# için bu UUID kullanılır. Faz 1'de gerçek JWT token decode edilir.
# Not: SQLite NUMERIC affinity sorununu aşmak için harf içerir ('a').
SYSTEM_USER_ID: _uuid.UUID = _uuid.UUID("00000000-0000-0000-0000-00000000000a")


def init_db() -> None:
    """Tüm tabloları oluşturur ve Faz 0 için seed verisi ekler.

    Faz 1'de bu fonksiyon kaldırılır; Alembic migration'ları devreye girer.
    Var olan tablolara dokunmaz (checkfirst=True davranışı).
    """
    # Tüm modeller __init__.py üzerinden import edilmiş olmalı
    # ki metadata'ya kayıtlı olsunlar.
    from app.models import (  # noqa: F401 — yan etki için import
        Class,
        Exam,
        Institution,
        LearningOutcome,
        RawExtraction,
        RawFile,
        Result,
        ReviewQueue,
        Student,
        Subject,
        Topic,
        User,
    )

    Base.metadata.create_all(bind=engine)

    # Faz 0: Sistem kullanıcısını seed et (auth yokken FK için gerekli)
    _seed_system_user()


def _seed_system_user() -> None:
    """Faz 0 sistem kullanıcısını oluşturur (yoksa).

    Bu kullanıcı auth yokken uploaded_by FK'si için kullanılır.
    Faz 1'de gerçek auth aktif edilince bu fonksiyon kaldırılır.
    """
    from app.models.user import User

    db = SessionLocal()
    try:
        exists = db.query(User).filter_by(id=SYSTEM_USER_ID).first()
        if not exists:
            system_user = User(
                id=SYSTEM_USER_ID,
                email="system@localhost",
                hashed_password="",  # Giriş yapılamaz — yalnızca FK referansı
                role="admin",
                is_active=False,  # Aktif değil; giriş yapılamaz
            )
            db.add(system_user)
            db.commit()
    finally:
        db.close()


def get_session() -> Generator[Session, None, None]:
    """FastAPI Depends() için session factory.

    Her HTTP isteği için ayrı bir DB oturumu açar ve
    istek tamamlandıktan sonra (hata olsa bile) kapatır.

    Kullanım:
        def endpoint(db: Session = Depends(get_session)):
            repo = StudentRepository(db)
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
FastAPI uygulama giriş noktası — Faz 0 Local MVP.

Faz 0 özellikleri:
  - Auth middleware YOK (ADR-007)
  - Startup'ta SQLite tabloları create_all ile oluşturulur
  - CORS tüm origin'lere açık (yerel geliştirme)
  - API prefix: /api/v1
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import analytics, classes, exams, review, students, upload
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başlangıç ve bitiş kancaları."""
    # ── Startup ──────────────────────────────────────────────────────────────
    # Faz 0: Tüm tabloları oluştur (Alembic yokken)
    init_db()

    # Upload dizinini oluştur (yoksa)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    # Gerekirse temizlik işlemleri buraya


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=("Öğrenci sınav performans analitik platformu. Faz 0 — Local MVP (Auth devre dışı, SQLite)."),
    lifespan=lifespan,
)

# ── CORS (Faz 0: tüm origin'lere açık) ───────────────────────────────────────
# Faz 1'de allow_origins daraltılır.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Router kayıtları ──────────────────────────────────────────────────────────
# Faz 0'da aktif endpoint'ler buraya eklenir.
# Her router kendi dosyasında tanımlı; main.py'ye sadece include edilir.


app.include_router(students.router, prefix="/api/v1/students", tags=["students"])
app.include_router(classes.router, prefix="/api/v1/classes", tags=["classes"])
app.include_router(exams.router, prefix="/api/v1/exams", tags=["exams"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])
app.include_router(review.router, prefix="/api/v1/review", tags=["review"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])


@app.get("/health", tags=["system"])
def health_check() -> dict:
    """Servis sağlık kontrolü.

    CI/CD ve manuel doğrulama için kullanılır.
    """
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "database": settings.DATABASE_URL,
        "auth_enabled": settings.AUTH_ENABLED,
    }

"""
Uygulama konfigürasyonu.

Pydantic Settings, değerleri şu sırayla okur:
  1. .env dosyası (varsa)
  2. Ortam değişkenleri
  3. Tanımlı default değerler

Faz 0 (Local MVP):
  - DATABASE_URL varsayılanı SQLite — kurulum sıfır bağımlılık.

Faz 1 geçişi (ADR-005):
  Tek yapılacak değişiklik .env dosyasında:
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dershane_db
  Servis veya repository koduna dokunulmaz.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Tüm uygulama ayarlarının tek toplama noktası."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Veritabanı ────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./dershane.db"
    # Faz 0: SQLite — proje dizininde tek dosya
    # Faz 1: "postgresql+asyncpg://user:pass@localhost:5432/dershane_db"
    # Değişiklik yalnızca bu satırda (veya .env'de) yapılır.

    # ── Dosya yükleme ─────────────────────────────────────────────────────────
    UPLOAD_DIR: Path = Path("./uploads/raw")
    # Pathlib.Path tipinde; kod içinde doğrudan / operatörüyle kullanılır.

    MAX_UPLOAD_SIZE_MB: int = 50

    # ── Uygulama ──────────────────────────────────────────────────────────────
    APP_TITLE: str = "Öğrenci Performans Analitik Platformu"
    APP_VERSION: str = "0.1.0-mvp"
    DEBUG: bool = True

    # ── Faz 0: Auth devre dışı (ADR-007) ─────────────────────────────────────
    # Faz 1'de aşağıdaki alanlar etkinleştirilecek:
    #   SECRET_KEY: str = "change_me"
    #   ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    AUTH_ENABLED: bool = False

    @property
    def is_sqlite(self) -> bool:
        """Geçerli veritabanı SQLite mi?"""
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def upload_dir(self) -> Path:
        """Upload dizini — her zaman Path nesnesi döner."""
        return Path(self.UPLOAD_DIR)


# Uygulama genelinde tek örnek
settings = Settings()

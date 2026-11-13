"""Конфигурация приложения.

Все пути и секреты — здесь, чтобы сервисы не знали, откуда берутся настройки.
"""
import os
import tempfile
from pathlib import Path
from typing import ClassVar

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Настройки рабочего запуска."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'finance.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Логи приложения (NFR-4): файл + журнал в БД
    LOG_FILE = os.environ.get("LOG_FILE", str(BASE_DIR / "logs" / "app.log"))

    # Безопасность сессии: cookie недоступна из JS, отправляется в том же сайте
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 часов

    JSON_AS_ASCII = False


class TestConfig(Config):
    """Настройки для тестов: отдельная БД в памяти, без отладочных эффектов."""

    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict] = {"connect_args": {"check_same_thread": False}}
    LOG_FILE = os.environ.get("TEST_LOG_FILE", str(Path(tempfile.gettempdir()) / "finance-test.log"))
    WTF_CSRF_ENABLED = False

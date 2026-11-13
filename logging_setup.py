"""Логирование: файл + консоль (NFR-4).

Журнал в БД (transaction_logs) отвечает за историю операций, файл — за диагностику:
входы, отказы, ошибки. В файл не попадают пароли и содержимое сессии.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import request


def configure_logging(app) -> None:
    if app.config.get("TESTING") and not app.config.get("LOG_FILE"):
        return

    log_path = Path(app.config["LOG_FILE"])
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)

    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False


def log_request(app, message: str, level: int = logging.INFO) -> None:
    """Пишет событие вместе с методом и путём запроса."""
    if request:
        message = f"{request.method} {request.path} — {message}"
    app.logger.log(level, message)

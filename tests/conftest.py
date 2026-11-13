"""Общие фикстуры тестов.

Каждый тест получает своё приложение и свою БД-файл — тесты не зависят друг от друга
и от порядка запуска (требование ЛР2).
"""
import pytest

from app import create_app
from config import TestConfig
from extensions import db


@pytest.fixture
def app(tmp_path):
    class Config(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'test.db'}"
        LOG_FILE = str(tmp_path / "test.log")

    application = create_app(Config)
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    with app.app_context():
        yield db.session


@pytest.fixture
def anonymous(client):
    return client

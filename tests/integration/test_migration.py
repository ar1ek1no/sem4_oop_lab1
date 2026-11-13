"""Тест миграции старой базы (версия 0.1 на tkinter) под веб-схему."""
import sqlite3

import pytest
from sqlalchemy import text

from app import create_app
from config import TestConfig
from extensions import db
from models import ACC_SAVING, Account, SalaryRequest, TransactionLog, User
from services.auth_service import AuthService

LEGACY_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    password VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    is_approved BOOLEAN
);
CREATE TABLE banks (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL);
CREATE TABLE enterprises (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL);
CREATE TABLE employment (
    user_id INTEGER,
    enterprise_id INTEGER,
    PRIMARY KEY (user_id, enterprise_id)
);
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    bank_id INTEGER,
    balance FLOAT,
    acc_type VARCHAR,
    is_blocked BOOLEAN
);
CREATE TABLE salary_requests (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    enterprise_id INTEGER,
    status VARCHAR
);
CREATE TABLE transaction_logs (
    id INTEGER PRIMARY KEY,
    sender_acc_id INTEGER,
    receiver_acc_id INTEGER,
    amount FLOAT,
    action_type VARCHAR,
    timestamp DATETIME,
    status VARCHAR,
    target_id INTEGER
);
INSERT INTO users (id, username, password, role, is_approved)
VALUES (1, 'oldclient', '123', 'client', 1),
       (2, 'oldadmin', '123', 'admin', 1),
       (3, 'pending', '123', 'client', 0);
INSERT INTO banks (id, name) VALUES (1, 'МТБанк');
INSERT INTO enterprises (id, name) VALUES (1, 'EPAM');
INSERT INTO employment (user_id, enterprise_id) VALUES (1, 1);
INSERT INTO accounts (id, user_id, bank_id, balance, acc_type, is_blocked)
VALUES (1, 1, 1, 1157.625, 'вклад?', 0), (2, 1, 1, -500.0, 'счет?', 1);
INSERT INTO salary_requests (id, user_id, enterprise_id, status) VALUES (1, 1, 1, 'approved');
INSERT INTO transaction_logs (id, sender_acc_id, receiver_acc_id, amount, action_type,
                              timestamp, status, target_id)
VALUES (1, NULL, 1, 1000.0, 'salary', '2026-10-01 10:00:00', 'completed', NULL);
"""


def build_legacy_db(path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(LEGACY_SCHEMA)
    connection.commit()
    connection.close()


@pytest.fixture
def legacy_app(tmp_path):
    db_path = tmp_path / "legacy.db"
    build_legacy_db(db_path)

    class LegacyConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        LOG_FILE = str(tmp_path / "legacy.log")

    application = create_app(LegacyConfig)
    yield application
    with application.app_context():
        db.session.remove()
    return application


def columns(engine, table):
    with engine.connect() as connection:
        return [row[1] for row in connection.execute(text(f"PRAGMA table_info({table})"))]


def test_plain_password_removed(legacy_app):
    with legacy_app.app_context():
        cols = columns(db.engine, "users")
        assert "password_hash" in cols
        assert "password" not in cols

        user = db.session.query(User).filter_by(username="oldclient").one()
        assert user.password_hash.startswith(("scrypt:", "pbkdf2:"))
        assert user.full_name == "oldclient"


def test_old_password_still_works(legacy_app):
    with legacy_app.app_context():
        ok, message, user = AuthService.authenticate("oldclient", "123")
        assert ok, message
        assert user.username == "oldclient"

        ok, message, _ = AuthService.authenticate("pending", "123")
        assert not ok
        assert "не подтверждена" in message


def test_account_type_normalized(legacy_app):
    with legacy_app.app_context():
        account = db.session.get(Account, 1)
        assert account.acc_type == ACC_SAVING
        assert account.is_closed is False
        assert account.created_at is not None

        blocked = db.session.get(Account, 2)
        assert blocked.acc_type == "checking"
        assert blocked.balance == -500.0


def test_legacy_logs_keep_no_payload(legacy_app):
    with legacy_app.app_context():
        log = db.session.get(TransactionLog, 1)
        assert log.payload is None
        assert log.actor_id is None


def test_salary_request_gets_timestamps(legacy_app):
    with legacy_app.app_context():
        request = db.session.get(SalaryRequest, 1)
        assert request.created_at is not None
        assert request.updated_at is not None
        assert request.last_paid_at is None


def test_migration_is_idempotent(tmp_path):
    db_path = tmp_path / "legacy.db"
    build_legacy_db(db_path)

    class LegacyConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        LOG_FILE = str(tmp_path / "legacy.log")

    first = create_app(LegacyConfig)
    with first.app_context():
        users_count = db.session.query(User).count()
        db.session.remove()

    second = create_app(LegacyConfig)
    with second.app_context():
        assert db.session.query(User).count() == users_count
        assert "password" not in columns(db.engine, "users")
        db.session.remove()

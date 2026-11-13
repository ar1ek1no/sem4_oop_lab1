"""Проверка логирования (NFR-4): действия и отказы попадают в файл журнала."""
from pathlib import Path

from tests.factories import create_account, create_bank, create_user


def test_login_and_transfer_are_logged(app, client):
    with app.app_context():
        user = create_user("client1")
        bank = create_bank()
        first = create_account(user, bank, balance=1000.0)
        second = create_account(user, bank, balance=0.0)
        ids = {"first": first.id, "second": second.id}

    client.post("/login", data={"username": "client1", "password": "secret123"})
    client.post("/transfer", data={"from_id": ids["first"], "to_id": ids["second"],
                                   "amount": "10"})

    log_text = Path(app.config["LOG_FILE"]).read_text(encoding="utf-8")
    assert "вход выполнен: client1" in log_text
    assert "перевод: перевод 10.00 BYN выполнен" in log_text


def test_failed_login_is_logged(app, client):
    with app.app_context():
        create_user("client1")

    client.post("/login", data={"username": "client1", "password": "wrong"})

    log_text = Path(app.config["LOG_FILE"]).read_text(encoding="utf-8")
    assert "неудачный вход" in log_text


def test_password_is_not_logged(app, client):
    with app.app_context():
        create_user("client1")

    client.post("/login", data={"username": "client1", "password": "secret123"})

    log_text = Path(app.config["LOG_FILE"]).read_text(encoding="utf-8")
    assert "secret123" not in log_text

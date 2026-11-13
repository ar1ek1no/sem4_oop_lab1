"""Юнит-тесты AuthService с моками репозитория: БД не нужна."""
from types import SimpleNamespace

from werkzeug.security import generate_password_hash

from services.auth_service import AuthService


def test_register_creates_only_client(monkeypatch):
    calls = {}
    monkeypatch.setattr("services.auth_service.UserRepository.get_by_username", lambda name: None)

    def fake_create(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(id=1)

    monkeypatch.setattr("services.auth_service.UserRepository.create", fake_create)

    ok, message = AuthService.register("newclient", "secret123", "Иванов Иван")

    assert ok is True
    assert "менеджер" in message
    assert calls["role"] == "client"
    assert calls["is_approved"] is False
    assert calls["password_hash"] != "secret123"


def test_register_rejects_duplicate(monkeypatch):
    monkeypatch.setattr(
        "services.auth_service.UserRepository.get_by_username",
        lambda name: SimpleNamespace(id=1),
    )
    ok, message = AuthService.register("taken", "secret123", "Иванов Иван")
    assert ok is False
    assert "занят" in message


def test_register_validates_fields(monkeypatch):
    monkeypatch.setattr("services.auth_service.UserRepository.get_by_username", lambda name: None)
    ok, message = AuthService.register("ab", "secret123", "Иванов Иван")
    assert ok is False and "логин" in message
    ok, message = AuthService.register("client", "123", "Иванов Иван")
    assert ok is False and "пароль" in message
    ok, message = AuthService.register("client", "secret123", "")
    assert ok is False and "ФИО" in message


def test_authenticate_ok(monkeypatch):
    user = SimpleNamespace(password_hash=generate_password_hash("secret123"),
                           is_rejected=False, is_approved=True)
    monkeypatch.setattr("services.auth_service.UserRepository.get_by_username", lambda name: user)

    ok, _message, result = AuthService.authenticate("client", "secret123")

    assert ok is True
    assert result is user


def test_authenticate_wrong_password(monkeypatch):
    user = SimpleNamespace(password_hash=generate_password_hash("secret123"),
                           is_rejected=False, is_approved=True)
    monkeypatch.setattr("services.auth_service.UserRepository.get_by_username", lambda name: user)

    ok, message, result = AuthService.authenticate("client", "wrong")

    assert ok is False
    assert result is None
    assert "неверный логин или пароль" in message


def test_authenticate_unknown_user(monkeypatch):
    monkeypatch.setattr("services.auth_service.UserRepository.get_by_username", lambda name: None)
    ok, _, result = AuthService.authenticate("nobody", "secret123")
    assert ok is False and result is None


def test_authenticate_unapproved(monkeypatch):
    user = SimpleNamespace(password_hash=generate_password_hash("secret123"),
                           is_rejected=False, is_approved=False)
    monkeypatch.setattr("services.auth_service.UserRepository.get_by_username", lambda name: user)
    ok, message, _ = AuthService.authenticate("client", "secret123")
    assert ok is False
    assert "не подтверждена" in message


def test_authenticate_rejected(monkeypatch):
    user = SimpleNamespace(password_hash=generate_password_hash("secret123"),
                           is_rejected=True, is_approved=True)
    monkeypatch.setattr("services.auth_service.UserRepository.get_by_username", lambda name: user)
    ok, message, _ = AuthService.authenticate("client", "secret123")
    assert ok is False
    assert "отклонена" in message

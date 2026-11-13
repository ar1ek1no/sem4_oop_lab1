"""Юнит-тесты AdminService: журнал и отмена через команды."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import services.admin_service as admin_module
import services.commands as commands_module
from models import ACTION_TRANSFER, ACTION_UNDO, LOG_CANCELLED, LOG_COMPLETED


@pytest.fixture
def logs(monkeypatch):
    mock = Mock()
    monkeypatch.setattr(admin_module, "LogRepository", mock)
    return mock


@pytest.fixture
def accounts(monkeypatch):
    mock = Mock()
    monkeypatch.setattr(commands_module, "AccountRepository", mock)
    return mock


def log(action_type=ACTION_TRANSFER, status=LOG_COMPLETED, payload=None, log_id=1):
    return SimpleNamespace(id=log_id, action_type=action_type, status=status,
                           payload=payload if payload is not None else {},
                           action_title="перевод")


def test_logs_delegates(logs):
    logs.get_all.return_value = ["a"]
    assert admin_module.AdminService.logs(10) == ["a"]
    logs.get_all.assert_called_once_with(10)


def test_undo_unknown_log(logs):
    logs.get_by_id.return_value = None
    ok, message = admin_module.AdminService.undo(1, 1)
    assert not ok and "не найдена" in message


def test_undo_already_cancelled(logs):
    logs.get_by_id.return_value = log(status=LOG_CANCELLED)
    ok, message = admin_module.AdminService.undo(1, 1)
    assert not ok and "уже отменено" in message


def test_undo_of_undo(logs):
    logs.get_by_id.return_value = log(action_type=ACTION_UNDO)
    ok, message = admin_module.AdminService.undo(1, 1)
    assert not ok and "нельзя" in message


def test_undo_legacy_without_payload(logs):
    logs.get_by_id.return_value = log(payload={})
    ok, message = admin_module.AdminService.undo(1, 1)
    assert not ok and "старой версией" in message


def test_undo_unsupported_action(logs):
    logs.get_by_id.return_value = log(action_type="unknown", payload={"a": 1})
    ok, message = admin_module.AdminService.undo(1, 1)
    assert not ok and "не поддерживается" in message


def test_undo_success(logs, accounts):
    target = log(payload={"from_id": 1, "to_id": 2, "amount": 50})
    logs.get_by_id.return_value = target
    accounts.get_by_id.side_effect = [
        SimpleNamespace(id=1, balance=100.0, is_blocked=False, is_closed=False),
        SimpleNamespace(id=2, balance=100.0, is_blocked=False, is_closed=False),
    ]

    ok, message = admin_module.AdminService.undo(1, 7)

    assert ok and "отменено" in message
    logs.mark_cancelled.assert_called_once_with(target)
    logs.create.assert_called_once()
    assert logs.create.call_args.args[0] == ACTION_UNDO
    assert logs.create.call_args.kwargs["actor_id"] == 7


def test_undo_rejected_by_command(logs, accounts):
    target = log(payload={"from_id": 1, "to_id": 2, "amount": 500})
    logs.get_by_id.return_value = target
    accounts.get_by_id.side_effect = [
        SimpleNamespace(id=1, balance=100.0, is_blocked=False, is_closed=False),
        SimpleNamespace(id=2, balance=10.0, is_blocked=False, is_closed=False),
    ]

    ok, message = admin_module.AdminService.undo(1, 7)

    assert not ok
    assert "нет этих средств" in message
    logs.mark_cancelled.assert_not_called()


def test_undo_unexpected_error_is_reraised(logs, monkeypatch):
    target = log(payload={"from_id": 1, "to_id": 2, "amount": 10})
    logs.get_by_id.return_value = target

    class Broken:
        def __init__(self, log):
            pass

        def undo(self):
            raise RuntimeError("boom")

    monkeypatch.setitem(admin_module.COMMANDS, ACTION_TRANSFER, Broken)
    with pytest.raises(RuntimeError):
        admin_module.AdminService.undo(1, 7)

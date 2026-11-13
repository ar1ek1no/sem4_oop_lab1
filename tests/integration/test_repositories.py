"""Интеграционные тесты моделей и репозиториев на реальной SQLite."""
import pytest

from models import (
    ACC_CHECKING,
    ACC_SAVING,
    ACTION_TRANSFER,
    REQ_APPROVED,
    ROLE_MANAGER,
    TransactionLog,
    utcnow,
)
from repositories.account_repository import AccountRepository
from repositories.log_repository import LogRepository
from repositories.salary_repository import SalaryRequestRepository
from repositories.user_repository import UserRepository
from tests.factories import (
    create_account,
    create_bank,
    create_enterprise,
    create_request,
    create_user,
)


def test_user_properties(app, db_session):
    client = create_user("client1")
    manager = create_user("manager1", role=ROLE_MANAGER)

    assert client.is_client is True
    assert client.is_manager is False
    assert client.is_admin is False
    assert manager.role_title == "менеджер"
    assert repr(client).startswith("<User")


def test_account_properties(app, db_session):
    client = create_user("client1")
    bank = create_bank("МТБанк")
    saving = create_account(client, bank, ACC_SAVING, 10.0)
    checking = create_account(client, bank, ACC_CHECKING, 5.0)

    assert saving.is_saving is True
    assert checking.is_saving is False
    assert saving.is_active is True
    assert saving.type_title == "вклад"
    assert "МТБанк" in saving.display_name

    saving.is_closed = True
    db_session.commit()
    assert saving.is_active is False


def test_salary_request_status_title(app, db_session):
    client = create_user("client1")
    enterprise = create_enterprise("EPAM")
    request = create_request(client, enterprise, REQ_APPROVED)
    assert request.status_title == "подтверждена"


def test_transaction_log_action_title(app, db_session):
    log = TransactionLog(action_type=ACTION_TRANSFER, amount=1.0)
    db_session.add(log)
    db_session.commit()
    assert log.action_title == "перевод"
    assert log.status == "completed"


def test_utcnow_is_naive_utc():
    assert utcnow().tzinfo is None


def test_user_repository(app, db_session):
    created = UserRepository.create("newuser", "hash", "Новый Пользователь")
    assert created.id
    assert UserRepository.get_by_username("newuser").id == created.id
    assert UserRepository.get_by_id(created.id).username == "newuser"
    assert UserRepository.get_by_username("missing") is None

    pending = UserRepository.get_pending_clients()
    assert created in pending

    UserRepository.approve(created)
    assert created.is_approved is True
    assert UserRepository.get_pending_clients() == []

    UserRepository.set_approved(created, False)
    assert created.is_approved is False

    UserRepository.reject(created)
    assert created.is_rejected is True
    assert UserRepository.get_pending_clients() == []

    UserRepository.update_rejected(created, False)
    assert created.is_rejected is False


def test_account_repository(app, db_session):
    client = create_user("client1")
    other = create_user("client2")
    bank = create_bank()
    account = AccountRepository.create(client.id, bank.id, ACC_SAVING)

    assert AccountRepository.get_by_id(account.id).id == account.id
    assert AccountRepository.get_for_user(account.id, client.id).id == account.id
    assert AccountRepository.get_for_user(account.id, other.id) is None

    AccountRepository.update(account, is_closed=True)
    assert AccountRepository.get_user_accounts(client.id) == []
    assert len(AccountRepository.get_user_accounts(client.id, include_closed=True)) == 1
    assert AccountRepository.get_all() != []

    AccountRepository.delete(account)
    assert AccountRepository.get_by_id(account.id) is None


def test_account_balances(app, db_session):
    client = create_user("client1")
    bank = create_bank()
    first = create_account(client, bank, ACC_CHECKING, 100.0)
    second = create_account(client, bank, ACC_CHECKING, 0.0)

    AccountRepository.move_funds(first, second, 40.0)
    assert first.balance == 60.0
    assert second.balance == 40.0

    AccountRepository.add_balance(second, 5.5)
    assert second.balance == 45.5


def test_salary_repository(app, db_session):
    client = create_user("client1")
    enterprise = create_enterprise("EPAM")
    pending = create_request(client, enterprise)

    assert SalaryRequestRepository.get_active(client.id, enterprise.id).id == pending.id
    assert SalaryRequestRepository.get_approved(client.id, enterprise.id) is None
    assert pending in SalaryRequestRepository.get_pending()
    assert SalaryRequestRepository.get_for_user(client.id) == [pending]
    assert SalaryRequestRepository.get_all() == [pending]

    SalaryRequestRepository.update(pending, status=REQ_APPROVED)
    assert SalaryRequestRepository.get_approved(client.id, enterprise.id).id == pending.id

    SalaryRequestRepository.delete(pending)
    assert SalaryRequestRepository.get_by_id(pending.id) is None


def test_log_repository(app, db_session):
    client = create_user("client1")
    bank = create_bank()
    account = create_account(client, bank, ACC_CHECKING, 100.0)

    log = LogRepository.create(ACTION_TRANSFER, amount=10.0, sender_acc_id=account.id,
                               receiver_acc_id=account.id, actor_id=client.id,
                               payload={"k": "v"})
    assert log.payload == {"k": "v"}
    assert LogRepository.get_by_id(log.id).id == log.id
    assert log in LogRepository.get_all()
    assert log in LogRepository.get_all(limit=1)
    assert log in LogRepository.get_for_accounts([account.id])
    assert LogRepository.get_for_accounts([]) == []

    LogRepository.mark_cancelled(log)
    assert log.status == "cancelled"

    LogRepository.rollback()


@pytest.mark.parametrize("limit", [None, 5])
def test_log_all_limits(app, db_session, limit):
    LogRepository.create(ACTION_TRANSFER, amount=1.0)
    assert len(LogRepository.get_all(limit)) == 1

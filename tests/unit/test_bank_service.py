"""Юнит-тесты BankService с моками репозиториев."""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from models import ACC_CHECKING, ACC_SAVING, ACTION_OPEN_ACCOUNT, ACTION_TRANSFER, utcnow
from services.bank_service import BankService


def account(account_id=1, balance=100.0, blocked=False, closed=False, acc_type=ACC_CHECKING,
            user_id=1):
    return SimpleNamespace(id=account_id, balance=balance, is_blocked=blocked, is_closed=closed,
                           acc_type=acc_type, user_id=user_id, type_title="счёт",
                           is_saving=acc_type == ACC_SAVING)


@pytest.fixture
def repos(monkeypatch):
    names = {
        "AccountRepository": Mock(),
        "BankRepository": Mock(),
        "EnterpriseRepository": Mock(),
        "EmploymentRepository": Mock(),
        "SalaryRequestRepository": Mock(),
        "LogRepository": Mock(),
    }
    for name, mock in names.items():
        monkeypatch.setattr(f"services.bank_service.{name}", mock)
    return names


class TestOpenAccount:
    def test_unknown_type(self, repos):
        ok, message = BankService.open_account(1, 1, "deposit")
        assert not ok and "тип" in message

    def test_bank_not_found(self, repos):
        repos["BankRepository"].get_by_id.return_value = None
        ok, message = BankService.open_account(1, 1, ACC_CHECKING)
        assert not ok and "банк не найден" in message

    def test_success_writes_log(self, repos):
        repos["BankRepository"].get_by_id.return_value = SimpleNamespace(id=2, name="Банк")
        repos["AccountRepository"].create.return_value = account(5)
        ok, message = BankService.open_account(1, 2, ACC_SAVING)
        assert ok and "№5" in message
        repos["AccountRepository"].create.assert_called_once_with(1, 2, ACC_SAVING)
        repos["LogRepository"].create.assert_called_once()
        assert repos["LogRepository"].create.call_args.args[0] == ACTION_OPEN_ACCOUNT


class TestCloseAccount:
    def test_foreign_account(self, repos):
        repos["AccountRepository"].get_for_user.return_value = None
        ok, message = BankService.close_account(1, 2)
        assert not ok and "не найден" in message

    def test_already_closed(self, repos):
        repos["AccountRepository"].get_for_user.return_value = account(closed=True)
        ok, message = BankService.close_account(1, 1)
        assert not ok and "уже закрыт" in message

    def test_blocked(self, repos):
        repos["AccountRepository"].get_for_user.return_value = account(blocked=True)
        ok, message = BankService.close_account(1, 1)
        assert not ok and "заблокирован" in message

    def test_non_zero_balance(self, repos):
        repos["AccountRepository"].get_for_user.return_value = account(balance=10)
        ok, message = BankService.close_account(1, 1)
        assert not ok and "нулевым" in message

    def test_success(self, repos):
        target = account(balance=0)
        repos["AccountRepository"].get_for_user.return_value = target
        ok, _message = BankService.close_account(1, 1)
        assert ok
        repos["AccountRepository"].update.assert_called_once_with(target, is_closed=True)


class TestTransfer:
    def test_invalid_amount(self, repos):
        ok, message = BankService.transfer(1, 1, 2, 0)
        assert not ok and "сумма" in message

    def test_same_account(self, repos):
        ok, message = BankService.transfer(1, 1, 1, 100)
        assert not ok and "тот же счёт" in message

    def test_sender_not_found(self, repos):
        repos["AccountRepository"].get_for_user.return_value = None
        ok, message = BankService.transfer(1, 1, 2, 100)
        assert not ok and "списания не найден" in message

    def test_sender_blocked(self, repos):
        repos["AccountRepository"].get_for_user.return_value = account(blocked=True)
        ok, message = BankService.transfer(1, 1, 2, 100)
        assert not ok and "заблокирован" in message

    def test_receiver_missing(self, repos):
        repos["AccountRepository"].get_for_user.return_value = account()
        repos["AccountRepository"].get_by_id.return_value = None
        ok, message = BankService.transfer(1, 1, 2, 100)
        assert not ok and "получателя не найден" in message

    def test_receiver_closed(self, repos):
        repos["AccountRepository"].get_for_user.return_value = account()
        repos["AccountRepository"].get_by_id.return_value = account(2, closed=True)
        ok, message = BankService.transfer(1, 1, 2, 100)
        assert not ok and "получателя закрыт" in message

    def test_receiver_blocked(self, repos):
        repos["AccountRepository"].get_for_user.return_value = account()
        repos["AccountRepository"].get_by_id.return_value = account(2, blocked=True)
        ok, message = BankService.transfer(1, 1, 2, 100)
        assert not ok and "получателя заблокирован" in message

    def test_insufficient_funds(self, repos):
        repos["AccountRepository"].get_for_user.return_value = account(balance=10)
        repos["AccountRepository"].get_by_id.return_value = account(2)
        ok, message = BankService.transfer(1, 1, 2, 100)
        assert not ok and "недостаточно" in message
        repos["AccountRepository"].move_funds.assert_not_called()

    def test_success(self, repos):
        sender = account(1, balance=500)
        receiver = account(2, balance=0)
        repos["AccountRepository"].get_for_user.return_value = sender
        repos["AccountRepository"].get_by_id.return_value = receiver

        ok, message = BankService.transfer(1, 1, 2, 100)

        assert ok and "выполнен" in message
        repos["AccountRepository"].move_funds.assert_called_once_with(sender, receiver, 100.0)
        repos["LogRepository"].create.assert_called_once()
        assert repos["LogRepository"].create.call_args.args[0] == ACTION_TRANSFER


class TestAccumulate:
    def test_no_savings(self, repos):
        repos["AccountRepository"].get_user_accounts.return_value = [account(acc_type=ACC_CHECKING)]
        ok, message = BankService.accumulate(1)
        assert not ok and "нет вкладов" in message

    def test_empty_balance(self, repos):
        repos["AccountRepository"].get_user_accounts.return_value = [
            account(acc_type=ACC_SAVING, balance=0),
        ]
        ok, message = BankService.accumulate(1)
        assert not ok and "нет вкладов" in message

    def test_blocked_savings_ignored(self, repos):
        repos["AccountRepository"].get_user_accounts.return_value = [
            account(acc_type=ACC_SAVING, blocked=True, balance=1000),
        ]
        ok, _ = BankService.accumulate(1)
        assert not ok

    def test_success(self, repos):
        saving = account(acc_type=ACC_SAVING, balance=1000)
        repos["AccountRepository"].get_user_accounts.return_value = [saving]
        ok, message = BankService.accumulate(1)
        assert ok and "1" in message
        repos["AccountRepository"].add_balance.assert_called_once_with(saving, 50.0)


class TestSalary:
    def test_apply_unknown_enterprise(self, repos):
        repos["EnterpriseRepository"].get_by_id.return_value = None
        ok, message = BankService.apply_for_salary(1, 1)
        assert not ok and "предприятие не найдено" in message

    def test_apply_duplicate(self, repos):
        repos["EnterpriseRepository"].get_by_id.return_value = SimpleNamespace(id=1, name="X")
        repos["SalaryRequestRepository"].get_active.return_value = SimpleNamespace(id=1)
        ok, message = BankService.apply_for_salary(1, 1)
        assert not ok and "уже подана" in message

    def test_apply_success(self, repos):
        repos["EnterpriseRepository"].get_by_id.return_value = SimpleNamespace(id=1, name="X")
        repos["SalaryRequestRepository"].get_active.return_value = None
        repos["SalaryRequestRepository"].create.return_value = SimpleNamespace(id=7)
        ok, message = BankService.apply_for_salary(1, 1)
        assert ok and "X" in message

    def test_pay_not_employed(self, repos):
        repos["EmploymentRepository"].get.return_value = None
        ok, message = BankService.pay_salary(1, 1, 1)
        assert not ok and "не являетесь сотрудником" in message

    def test_pay_without_approved_request(self, repos):
        repos["EmploymentRepository"].get.return_value = SimpleNamespace(salary_amount=1000)
        repos["SalaryRequestRepository"].get_approved.return_value = None
        ok, message = BankService.pay_salary(1, 1, 1)
        assert not ok and "подтверждённой заявки" in message

    def test_pay_already_paid_this_month(self, repos):
        repos["EmploymentRepository"].get.return_value = SimpleNamespace(salary_amount=1000)
        repos["SalaryRequestRepository"].get_approved.return_value = SimpleNamespace(
            id=3, last_paid_at=utcnow(),
        )
        ok, message = BankService.pay_salary(1, 1, 1)
        assert not ok and "уже выплачена" in message

    def test_pay_previous_month_allowed(self, repos):
        repos["EmploymentRepository"].get.return_value = SimpleNamespace(salary_amount=1000)
        request = SimpleNamespace(id=3, last_paid_at=utcnow() - timedelta(days=40))
        repos["SalaryRequestRepository"].get_approved.return_value = request
        target = account(balance=0)
        repos["AccountRepository"].get_for_user.return_value = target
        ok, message = BankService.pay_salary(1, 1, 1)
        assert ok and "зачислена" in message
        repos["AccountRepository"].add_balance.assert_called_once_with(target, 1000.0)

    def test_pay_account_blocked(self, repos):
        repos["EmploymentRepository"].get.return_value = SimpleNamespace(salary_amount=1000)
        repos["SalaryRequestRepository"].get_approved.return_value = SimpleNamespace(
            id=3, last_paid_at=None,
        )
        repos["AccountRepository"].get_for_user.return_value = account(blocked=True)
        ok, message = BankService.pay_salary(1, 1, 1)
        assert not ok and "заблокирован" in message


def test_history_uses_all_accounts(repos):
    repos["AccountRepository"].get_user_accounts.return_value = [account(1), account(2, closed=True)]
    repos["LogRepository"].get_for_accounts.return_value = []
    BankService.history(1)
    repos["AccountRepository"].get_user_accounts.assert_called_once_with(1, include_closed=True)
    repos["LogRepository"].get_for_accounts.assert_called_once_with([1, 2])

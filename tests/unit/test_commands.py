"""Юнит-тесты команд отмены (паттерн Command)."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import services.commands as commands_module
from models import (
    ACTION_ACCUMULATE,
    ACTION_APPLY_SALARY,
    ACTION_APPROVE_SALARY,
    ACTION_APPROVE_USER,
    ACTION_BLOCK,
    ACTION_CLOSE_ACCOUNT,
    ACTION_FIRE_EMPLOYEE,
    ACTION_OPEN_ACCOUNT,
    ACTION_REJECT_SALARY,
    ACTION_REJECT_USER,
    ACTION_REVOKE_SALARY,
    ACTION_SALARY,
    ACTION_TRANSFER,
    ACTION_UNBLOCK,
    REQ_APPROVED,
    REQ_PENDING,
)
from services.commands import UndoError


def make_log(action_type, **payload):
    return SimpleNamespace(id=1, action_type=action_type, payload=payload)


def account(account_id=1, balance=100.0, blocked=False, closed=False):
    return SimpleNamespace(id=account_id, balance=balance, is_blocked=blocked,
                           is_closed=closed)


@pytest.fixture
def repos(monkeypatch):
    mocks = {
        name: Mock()
        for name in ("AccountRepository", "EmploymentRepository",
                     "SalaryRequestRepository", "UserRepository")
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(commands_module, name, mock)
    return mocks


class TestAccountCommands:
    def test_open_account_missing(self, repos):
        repos["AccountRepository"].get_by_id.return_value = None
        with pytest.raises(UndoError):
            commands_module.OpenAccountCommand(make_log(ACTION_OPEN_ACCOUNT, account_id=1)).undo()

    def test_open_account_with_balance(self, repos):
        repos["AccountRepository"].get_by_id.return_value = account(balance=10)
        with pytest.raises(UndoError):
            commands_module.OpenAccountCommand(make_log(ACTION_OPEN_ACCOUNT, account_id=1)).undo()

    def test_open_account_success(self, repos):
        target = account(balance=0)
        repos["AccountRepository"].get_by_id.return_value = target
        commands_module.OpenAccountCommand(make_log(ACTION_OPEN_ACCOUNT, account_id=1)).undo()
        repos["AccountRepository"].update.assert_called_once_with(target, is_closed=True)

    def test_close_account_already_open(self, repos):
        repos["AccountRepository"].get_by_id.return_value = account(closed=False)
        with pytest.raises(UndoError):
            commands_module.CloseAccountCommand(make_log(ACTION_CLOSE_ACCOUNT, account_id=1)).undo()

    def test_close_account_success(self, repos):
        target = account(closed=True)
        repos["AccountRepository"].get_by_id.return_value = target
        commands_module.CloseAccountCommand(make_log(ACTION_CLOSE_ACCOUNT, account_id=1)).undo()
        repos["AccountRepository"].update.assert_called_once_with(target, is_closed=False)

    def test_transfer_missing_receiver(self, repos):
        repos["AccountRepository"].get_by_id.side_effect = [account(1), None]
        with pytest.raises(UndoError):
            commands_module.TransferCommand(
                make_log(ACTION_TRANSFER, from_id=1, to_id=2, amount=50),
            ).undo()

    def test_transfer_not_enough_on_receiver(self, repos):
        repos["AccountRepository"].get_by_id.side_effect = [account(1), account(2, balance=10)]
        with pytest.raises(UndoError):
            commands_module.TransferCommand(
                make_log(ACTION_TRANSFER, from_id=1, to_id=2, amount=50),
            ).undo()

    def test_transfer_success_reverses(self, repos):
        sender, receiver = account(1), account(2)
        repos["AccountRepository"].get_by_id.side_effect = [sender, receiver]

        commands_module.TransferCommand(
            make_log(ACTION_TRANSFER, from_id=1, to_id=2, amount=50),
        ).undo()

        repos["AccountRepository"].move_funds.assert_called_once_with(receiver, sender, 50.0)

    def test_block_and_unblock(self, repos):
        target = account()
        repos["AccountRepository"].get_by_id.return_value = target

        commands_module.BlockCommand(make_log(ACTION_BLOCK, account_id=1, previous=False)).undo()
        assert repos["AccountRepository"].update.call_args.kwargs["is_blocked"] is False

        commands_module.UnblockCommand(make_log(ACTION_UNBLOCK, account_id=1, previous=True)).undo()
        assert repos["AccountRepository"].update.call_args.kwargs["is_blocked"] is True


class TestSalaryCommands:
    def test_salary_not_enough_money(self, repos):
        repos["AccountRepository"].get_by_id.return_value = account(balance=10)
        with pytest.raises(UndoError):
            commands_module.SalaryCommand(
                make_log(ACTION_SALARY, account_id=1, amount=1000, request_id=3),
            ).undo()

    def test_salary_success(self, repos):
        target = account(balance=1000)
        request = SimpleNamespace(last_paid_at=object())
        repos["AccountRepository"].get_by_id.return_value = target
        repos["SalaryRequestRepository"].get_by_id.return_value = request

        commands_module.SalaryCommand(
            make_log(ACTION_SALARY, account_id=1, amount=1000, request_id=3),
        ).undo()

        repos["AccountRepository"].add_balance.assert_called_once_with(target, -1000.0)
        repos["SalaryRequestRepository"].update.assert_called_once_with(request,
                                                                        last_paid_at=None)

    def test_accumulate_without_items(self, repos):
        with pytest.raises(UndoError):
            commands_module.AccumulateCommand(make_log(ACTION_ACCUMULATE)).undo()

    def test_accumulate_not_enough(self, repos):
        repos["AccountRepository"].get_by_id.return_value = account(balance=1)
        with pytest.raises(UndoError):
            commands_module.AccumulateCommand(
                make_log(ACTION_ACCUMULATE, items=[{"account_id": 1, "bonus": 5}]),
            ).undo()

    def test_accumulate_success(self, repos):
        first, second = account(1, balance=100), account(2, balance=200)
        repos["AccountRepository"].get_by_id.side_effect = [first, second]

        commands_module.AccumulateCommand(
            make_log(ACTION_ACCUMULATE, items=[{"account_id": 1, "bonus": 5},
                                               {"account_id": 2, "bonus": 10}]),
        ).undo()

        assert repos["AccountRepository"].add_balance.call_count == 2
        repos["AccountRepository"].add_balance.assert_any_call(first, -5.0)
        repos["AccountRepository"].add_balance.assert_any_call(second, -10.0)


class TestUserCommands:
    def test_approve_user_missing(self, repos):
        repos["UserRepository"].get_by_id.return_value = None
        with pytest.raises(UndoError):
            commands_module.ApproveUserCommand(
                make_log(ACTION_APPROVE_USER, user_id=5)).undo()

    def test_approve_user_already_unapproved(self, repos):
        repos["UserRepository"].get_by_id.return_value = SimpleNamespace(is_approved=False)
        with pytest.raises(UndoError):
            commands_module.ApproveUserCommand(
                make_log(ACTION_APPROVE_USER, user_id=5)).undo()

    def test_approve_user_success(self, repos):
        target = SimpleNamespace(is_approved=True)
        repos["UserRepository"].get_by_id.return_value = target
        commands_module.ApproveUserCommand(make_log(ACTION_APPROVE_USER, user_id=5)).undo()
        repos["UserRepository"].set_approved.assert_called_once_with(target, False)

    def test_reject_user_success(self, repos):
        target = SimpleNamespace(is_rejected=True)
        repos["UserRepository"].get_by_id.return_value = target
        commands_module.RejectUserCommand(make_log(ACTION_REJECT_USER, user_id=5)).undo()
        repos["UserRepository"].update_rejected.assert_called_once_with(target, False)

    def test_reject_user_not_rejected(self, repos):
        repos["UserRepository"].get_by_id.return_value = SimpleNamespace(is_rejected=False)
        with pytest.raises(UndoError):
            commands_module.RejectUserCommand(make_log(ACTION_REJECT_USER, user_id=5)).undo()


class TestRequestCommands:
    def test_apply_salary_already_decided(self, repos):
        repos["SalaryRequestRepository"].get_by_id.return_value = SimpleNamespace(
            status=REQ_APPROVED,
        )
        with pytest.raises(UndoError):
            commands_module.ApplySalaryCommand(make_log(ACTION_APPLY_SALARY, request_id=1)).undo()

    def test_apply_salary_success(self, repos):
        request = SimpleNamespace(status=REQ_PENDING)
        repos["SalaryRequestRepository"].get_by_id.return_value = request
        commands_module.ApplySalaryCommand(make_log(ACTION_APPLY_SALARY, request_id=1)).undo()
        repos["SalaryRequestRepository"].delete.assert_called_once_with(request)

    def test_approve_salary_with_existing_employment(self, repos):
        request = SimpleNamespace(status=REQ_APPROVED, user_id=5, enterprise_id=2)
        employment = SimpleNamespace(salary_amount=900)
        repos["SalaryRequestRepository"].get_by_id.return_value = request
        repos["EmploymentRepository"].get.return_value = employment

        commands_module.ApproveSalaryCommand(make_log(
            ACTION_APPROVE_SALARY, request_id=1, employment_created=False, previous_salary=800,
        )).undo()

        repos["EmploymentRepository"].update_salary.assert_called_once_with(employment, 800)
        repos["SalaryRequestRepository"].update.assert_called_once_with(request,
                                                                        status=REQ_PENDING)

    def test_approve_salary_removes_new_employment(self, repos):
        request = SimpleNamespace(status=REQ_APPROVED, user_id=5, enterprise_id=2)
        employment = SimpleNamespace(salary_amount=900)
        repos["SalaryRequestRepository"].get_by_id.return_value = request
        repos["EmploymentRepository"].get.return_value = employment

        commands_module.ApproveSalaryCommand(make_log(
            ACTION_APPROVE_SALARY, request_id=1, employment_created=True,
        )).undo()

        repos["EmploymentRepository"].remove.assert_called_once_with(employment)

    def test_reject_salary_undo(self, repos):
        request = SimpleNamespace(status="rejected")
        repos["SalaryRequestRepository"].get_by_id.return_value = request
        commands_module.RejectSalaryCommand(make_log(ACTION_REJECT_SALARY, request_id=1)).undo()
        repos["SalaryRequestRepository"].update.assert_called_once_with(request,
                                                                        status=REQ_PENDING)

    def test_revoke_salary_restores_employment(self, repos):
        request = SimpleNamespace(status=REQ_PENDING, user_id=5, enterprise_id=2)
        repos["SalaryRequestRepository"].get_by_id.return_value = request
        repos["EmploymentRepository"].get.return_value = None

        commands_module.RevokeSalaryCommand(make_log(
            ACTION_REVOKE_SALARY, request_id=1, salary_amount=1200,
        )).undo()

        repos["SalaryRequestRepository"].update.assert_called_once_with(request,
                                                                        status=REQ_APPROVED)
        repos["EmploymentRepository"].add.assert_called_once_with(5, 2, 1200)

    def test_fire_employee_restores(self, repos):
        repos["EmploymentRepository"].get.return_value = None
        commands_module.FireEmployeeCommand(make_log(
            ACTION_FIRE_EMPLOYEE, user_id=5, enterprise_id=2, salary_amount=1100,
        )).undo()
        repos["EmploymentRepository"].add.assert_called_once_with(5, 2, 1100)

    def test_fire_employee_already_restored(self, repos):
        repos["EmploymentRepository"].get.return_value = SimpleNamespace()
        with pytest.raises(UndoError):
            commands_module.FireEmployeeCommand(make_log(
                ACTION_FIRE_EMPLOYEE, user_id=5, enterprise_id=2,
            )).undo()


def test_all_actions_have_command():
    assert len(commands_module.COMMANDS) >= 14
    assert ACTION_TRANSFER in commands_module.COMMANDS

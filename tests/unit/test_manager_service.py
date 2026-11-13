"""Юнит-тесты ManagerService с моками репозиториев."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from models import DEFAULT_SALARY, REQ_APPROVED, REQ_PENDING, REQ_REJECTED, ROLE_CLIENT
from services.manager_service import ManagerService


@pytest.fixture
def repos(monkeypatch):
    names = {
        "AccountRepository": Mock(),
        "EnterpriseRepository": Mock(),
        "EmploymentRepository": Mock(),
        "SalaryRequestRepository": Mock(),
        "LogRepository": Mock(),
        "UserRepository": Mock(),
    }
    for name, mock in names.items():
        monkeypatch.setattr(f"services.manager_service.{name}", mock)
    return names


def user(**fields):
    defaults = {"id": 5, "username": "client", "role": ROLE_CLIENT, "is_approved": False,
                "is_rejected": False}
    defaults.update(fields)
    return SimpleNamespace(**defaults)


class TestApproveClient:
    def test_not_found(self, repos):
        repos["UserRepository"].get_by_id.return_value = None
        ok, message = ManagerService.approve_client(1, 99)
        assert not ok and "не найден" in message

    def test_not_a_client(self, repos):
        repos["UserRepository"].get_by_id.return_value = user(role="manager")
        ok, message = ManagerService.approve_client(1, 5)
        assert not ok and "не найден" in message

    def test_already_rejected(self, repos):
        repos["UserRepository"].get_by_id.return_value = user(is_rejected=True)
        ok, message = ManagerService.approve_client(1, 5)
        assert not ok and "отклонена" in message

    def test_already_approved(self, repos):
        repos["UserRepository"].get_by_id.return_value = user(is_approved=True)
        ok, message = ManagerService.approve_client(1, 5)
        assert not ok and "уже подтверждена" in message

    def test_success(self, repos):
        target = user()
        repos["UserRepository"].get_by_id.return_value = target
        ok, message = ManagerService.approve_client(1, 5)
        assert ok and "подтверждён" in message
        repos["UserRepository"].approve.assert_called_once_with(target)
        repos["LogRepository"].create.assert_called_once()


class TestRejectClient:
    def test_not_found(self, repos):
        repos["UserRepository"].get_by_id.return_value = None
        ok, message = ManagerService.reject_client(1, 99)
        assert not ok and "не найден" in message

    def test_already_rejected(self, repos):
        repos["UserRepository"].get_by_id.return_value = user(is_rejected=True)
        ok, message = ManagerService.reject_client(1, 5)
        assert not ok and "уже отклонена" in message

    def test_success(self, repos):
        target = user()
        repos["UserRepository"].get_by_id.return_value = target
        ok, message = ManagerService.reject_client(1, 5)
        assert ok and "отклонена" in message
        repos["UserRepository"].update_rejected.assert_called_once_with(target, True)


class TestRequests:
    def request(self, status=REQ_PENDING, request_id=1):
        return SimpleNamespace(id=request_id, status=status, user_id=5, enterprise_id=2,
                               user=SimpleNamespace(username="client"),
                               enterprise=SimpleNamespace(name="ООО"))

    def test_approve_invalid_salary(self, repos):
        ok, message = ManagerService.approve_request(1, 1, -5)
        assert not ok and "сумма" in message

    def test_approve_not_found(self, repos):
        repos["SalaryRequestRepository"].get_by_id.return_value = None
        ok, message = ManagerService.approve_request(1, 1, 1000)
        assert not ok and "не найдена" in message

    def test_approve_already_decided(self, repos):
        repos["SalaryRequestRepository"].get_by_id.return_value = self.request(REQ_APPROVED)
        ok, message = ManagerService.approve_request(1, 1, 1000)
        assert not ok and "уже рассмотрена" in message

    def test_approve_creates_employment(self, repos):
        request = self.request()
        repos["SalaryRequestRepository"].get_by_id.return_value = request
        repos["EmploymentRepository"].get.return_value = None
        ok, _message = ManagerService.approve_request(1, 1, 1500)
        assert ok
        repos["SalaryRequestRepository"].update.assert_called_once_with(request,
                                                                        status=REQ_APPROVED)
        repos["EmploymentRepository"].add.assert_called_once_with(5, 2, 1500)

    def test_approve_updates_existing_salary(self, repos):
        request = self.request()
        repos["SalaryRequestRepository"].get_by_id.return_value = request
        repos["EmploymentRepository"].get.return_value = SimpleNamespace(salary_amount=1000)
        ok, _ = ManagerService.approve_request(1, 1, DEFAULT_SALARY)
        assert ok
        repos["EmploymentRepository"].update_salary.assert_called_once()

    def test_reject_success(self, repos):
        request = self.request()
        repos["SalaryRequestRepository"].get_by_id.return_value = request
        ok, message = ManagerService.reject_request(1, 1)
        assert ok and "отклонена" in message
        repos["SalaryRequestRepository"].update.assert_called_once_with(request,
                                                                        status=REQ_REJECTED)

    def test_reject_not_pending(self, repos):
        repos["SalaryRequestRepository"].get_by_id.return_value = self.request(REQ_REJECTED)
        ok, message = ManagerService.reject_request(1, 1)
        assert not ok and "уже рассмотрена" in message

    def test_revoke_ok(self, repos):
        request = self.request(REQ_APPROVED)
        repos["SalaryRequestRepository"].get_by_id.return_value = request
        repos["EmploymentRepository"].get.return_value = SimpleNamespace(salary_amount=1000)
        ok, message = ManagerService.revoke_request(1, 1)
        assert ok and "отозвано" in message
        repos["EmploymentRepository"].remove.assert_called_once()

    def test_revoke_not_approved(self, repos):
        repos["SalaryRequestRepository"].get_by_id.return_value = self.request(REQ_PENDING)
        ok, message = ManagerService.revoke_request(1, 1)
        assert not ok and "только подтверждённую" in message


class TestBlocking:
    def test_not_found(self, repos):
        repos["AccountRepository"].get_by_id.return_value = None
        ok, message = ManagerService.set_blocked(1, 1, True)
        assert not ok and "не найден" in message

    def test_closed(self, repos):
        repos["AccountRepository"].get_by_id.return_value = SimpleNamespace(is_closed=True,
                                                                           is_blocked=False,
                                                                           id=1)
        ok, message = ManagerService.set_blocked(1, 1, True)
        assert not ok and "закрыт" in message

    def test_same_state(self, repos):
        repos["AccountRepository"].get_by_id.return_value = SimpleNamespace(is_closed=False,
                                                                           is_blocked=True,
                                                                           id=1)
        ok, message = ManagerService.set_blocked(1, 1, True)
        assert not ok and "уже в этом состоянии" in message

    def test_block_and_unblock(self, repos):
        target = SimpleNamespace(is_closed=False, is_blocked=False, id=1)
        repos["AccountRepository"].get_by_id.return_value = target
        ok, message = ManagerService.set_blocked(1, 1, True)
        assert ok and "заблокирован" in message
        target.is_blocked = True
        ok, message = ManagerService.set_blocked(1, 1, False)
        assert ok and "разблокирован" in message


class TestStaff:
    def test_fire_not_found(self, repos):
        repos["EmploymentRepository"].get.return_value = None
        ok, message = ManagerService.fire_employee(1, 5, 2)
        assert not ok and "не найден" in message

    def test_fire_success(self, repos):
        employment = SimpleNamespace(salary_amount=1200)
        repos["EmploymentRepository"].get.return_value = employment
        ok, message = ManagerService.fire_employee(1, 5, 2)
        assert ok and "уволен" in message
        repos["EmploymentRepository"].remove.assert_called_once_with(employment)
        payload = repos["LogRepository"].create.call_args.kwargs["payload"]
        assert payload["salary_amount"] == 1200

    def test_delegation(self, repos):
        repos["UserRepository"].get_pending_clients.return_value = ["a"]
        assert ManagerService.pending_clients() == ["a"]
        repos["AccountRepository"].get_all.return_value = ["b"]
        assert ManagerService.accounts() == ["b"]
        repos["EnterpriseRepository"].get_all.return_value = ["c"]
        assert ManagerService.enterprises() == ["c"]
        repos["EmploymentRepository"].get_for_enterprise.return_value = ["d"]
        assert ManagerService.staff(2) == ["d"]
        repos["SalaryRequestRepository"].get_all.return_value = ["e"]
        assert ManagerService.all_requests() == ["e"]

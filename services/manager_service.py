"""Операции менеджера: подтверждение клиентов и заявок, блокировки, штат.

Отдельный сервис, потому что у менеджера свои правила: он меняет состояние чужих
объектов и каждое изменение обязано попасть в журнал (NFR-4, FR-3, FR-14).
"""
from models import (
    ACTION_APPROVE_SALARY,
    ACTION_APPROVE_USER,
    ACTION_BLOCK,
    ACTION_FIRE_EMPLOYEE,
    ACTION_REJECT_SALARY,
    ACTION_REJECT_USER,
    ACTION_REVOKE_SALARY,
    ACTION_UNBLOCK,
    DEFAULT_SALARY,
    REQ_APPROVED,
    REQ_PENDING,
    REQ_REJECTED,
    ROLE_CLIENT,
)
from repositories.account_repository import AccountRepository
from repositories.employment_repository import EmploymentRepository
from repositories.enterprise_repository import EnterpriseRepository
from repositories.log_repository import LogRepository
from repositories.salary_repository import SalaryRequestRepository
from repositories.user_repository import UserRepository
from services.validators import check_amount_value


class ManagerService:
    # --- клиенты ---------------------------------------------------------
    @staticmethod
    def pending_clients() -> list:
        return UserRepository.get_pending_clients()

    @staticmethod
    def approve_client(manager_id: int, user_id: int) -> tuple[bool, str]:
        user = UserRepository.get_by_id(user_id)
        if user is None or user.role != ROLE_CLIENT:
            return False, "клиент не найден"
        if user.is_rejected:
            return False, "регистрация уже отклонена"
        if user.is_approved:
            return False, "регистрация уже подтверждена"
        UserRepository.approve(user)
        LogRepository.create(
            ACTION_APPROVE_USER, actor_id=manager_id, payload={"user_id": user.id},
        )
        return True, f"клиент {user.username} подтверждён"

    @staticmethod
    def reject_client(manager_id: int, user_id: int) -> tuple[bool, str]:
        user = UserRepository.get_by_id(user_id)
        if user is None or user.role != ROLE_CLIENT:
            return False, "клиент не найден"
        if user.is_rejected:
            return False, "регистрация уже отклонена"
        UserRepository.update_rejected(user, True)
        LogRepository.create(
            ACTION_REJECT_USER, actor_id=manager_id, payload={"user_id": user.id},
        )
        return True, f"регистрация {user.username} отклонена"

    # --- заявки на зарплатный проект -------------------------------------
    @staticmethod
    def pending_requests() -> list:
        return SalaryRequestRepository.get_pending()

    @staticmethod
    def all_requests() -> list:
        return SalaryRequestRepository.get_all()

    @staticmethod
    def approve_request(manager_id: int, request_id: int,
                        salary_amount: float = DEFAULT_SALARY) -> tuple[bool, str]:
        error = check_amount_value(salary_amount)
        if error:
            return False, error
        salary_amount = round(float(salary_amount), 2)
        request = SalaryRequestRepository.get_by_id(request_id)
        if request is None:
            return False, "заявка не найдена"
        if request.status != REQ_PENDING:
            return False, "заявка уже рассмотрена"

        SalaryRequestRepository.update(request, status=REQ_APPROVED)
        employment = EmploymentRepository.get(request.user_id, request.enterprise_id)
        previous_salary = None
        if employment is None:
            EmploymentRepository.add(request.user_id, request.enterprise_id, salary_amount)
        else:
            previous_salary = employment.salary_amount
            EmploymentRepository.update_salary(employment, salary_amount)
        LogRepository.create(
            ACTION_APPROVE_SALARY,
            actor_id=manager_id,
            payload={"request_id": request.id, "user_id": request.user_id,
                     "enterprise_id": request.enterprise_id, "salary_amount": salary_amount,
                     "employment_created": previous_salary is None,
                     "previous_salary": previous_salary},
        )
        return True, "заявка подтверждена, сотрудник добавлен в штат"

    @staticmethod
    def reject_request(manager_id: int, request_id: int) -> tuple[bool, str]:
        request = SalaryRequestRepository.get_by_id(request_id)
        if request is None:
            return False, "заявка не найдена"
        if request.status != REQ_PENDING:
            return False, "заявка уже рассмотрена"
        SalaryRequestRepository.update(request, status=REQ_REJECTED)
        LogRepository.create(
            ACTION_REJECT_SALARY,
            actor_id=manager_id,
            payload={"request_id": request.id, "user_id": request.user_id,
                     "enterprise_id": request.enterprise_id},
        )
        return True, "заявка отклонена"

    @staticmethod
    def revoke_request(manager_id: int, request_id: int) -> tuple[bool, str]:
        request = SalaryRequestRepository.get_by_id(request_id)
        if request is None:
            return False, "заявка не найдена"
        if request.status != REQ_APPROVED:
            return False, "отозвать можно только подтверждённую заявку"
        SalaryRequestRepository.update(request, status=REQ_PENDING)
        employment = EmploymentRepository.get(request.user_id, request.enterprise_id)
        salary = employment.salary_amount if employment else DEFAULT_SALARY
        if employment is not None:
            EmploymentRepository.remove(employment)
        LogRepository.create(
            ACTION_REVOKE_SALARY,
            actor_id=manager_id,
            payload={"request_id": request.id, "user_id": request.user_id,
                     "enterprise_id": request.enterprise_id, "salary_amount": salary},
        )
        return True, "подтверждение отозвано, сотрудник убран из штата"

    # --- счета -----------------------------------------------------------
    @staticmethod
    def accounts() -> list:
        return AccountRepository.get_all()

    @staticmethod
    def set_blocked(manager_id: int, account_id: int, blocked: bool) -> tuple[bool, str]:
        account = AccountRepository.get_by_id(account_id)
        if account is None:
            return False, "счёт не найден"
        if account.is_closed:
            return False, "счёт закрыт — блокировка недоступна"
        if account.is_blocked == blocked:
            return False, "счёт уже в этом состоянии"
        previous = account.is_blocked
        AccountRepository.update(account, is_blocked=blocked)
        LogRepository.create(
            ACTION_BLOCK if blocked else ACTION_UNBLOCK,
            receiver_acc_id=account.id,
            actor_id=manager_id,
            payload={"account_id": account.id, "previous": previous},
        )
        return True, "счёт заблокирован" if blocked else "счёт разблокирован"

    # --- предприятия и штат ----------------------------------------------
    @staticmethod
    def enterprises() -> list:
        return EnterpriseRepository.get_all()

    @staticmethod
    def staff(enterprise_id: int) -> list:
        return EmploymentRepository.get_for_enterprise(enterprise_id)

    @staticmethod
    def fire_employee(manager_id: int, user_id: int, enterprise_id: int) -> tuple[bool, str]:
        employment = EmploymentRepository.get(user_id, enterprise_id)
        if employment is None:
            return False, "сотрудник не найден в штате"
        salary = employment.salary_amount
        EmploymentRepository.remove(employment)
        LogRepository.create(
            ACTION_FIRE_EMPLOYEE,
            actor_id=manager_id,
            payload={"user_id": user_id, "enterprise_id": enterprise_id, "salary_amount": salary},
        )
        return True, "сотрудник уволен"

    # --- история клиента ------------------------------------------------
    @staticmethod
    def user_history(user_id: int) -> list:
        account_ids = [
            account.id
            for account in AccountRepository.get_user_accounts(user_id, include_closed=True)
        ]
        return LogRepository.get_for_accounts(account_ids)

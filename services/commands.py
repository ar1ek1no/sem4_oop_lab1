"""Отмена действий: паттерн Command (ISSUE-5).

Каждое действие журнала — отдельный класс с одним методом `undo()`. Добавление новой
операции не требует править общий `if/elif`: достаточно зарегистрировать класс в
`COMMANDS`. Данные для отката лежат в `payload` записи журнала, а не «упакованы»
в чужие поля вроде `amount`/`target_id`.
"""
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
from repositories.account_repository import AccountRepository
from repositories.employment_repository import EmploymentRepository
from repositories.salary_repository import SalaryRequestRepository
from repositories.user_repository import UserRepository


class UndoError(Exception):
    """Отмена невозможна: состояние уже изменилось или данных не хватает."""


class Command:
    """Базовый класс: хранит запись журнала и её payload."""

    action_type = ""

    def __init__(self, log):
        self.log = log
        self.data = log.payload or {}

    def undo(self) -> None:  # pragma: no cover - переопределяется
        raise NotImplementedError

    def _account(self, account_id, label="счёт"):
        account = AccountRepository.get_by_id(account_id)
        if account is None:
            raise UndoError(f"{label} №{account_id} не найден — отмена невозможна")
        return account


class OpenAccountCommand(Command):
    action_type = ACTION_OPEN_ACCOUNT

    def undo(self) -> None:
        account = self._account(self.data.get("account_id"))
        if account.is_closed:
            raise UndoError("счёт уже закрыт")
        if abs(account.balance) > 0.001:
            raise UndoError("на счёте есть средства — сначала переведите их")
        AccountRepository.update(account, is_closed=True)


class CloseAccountCommand(Command):
    action_type = ACTION_CLOSE_ACCOUNT

    def undo(self) -> None:
        account = self._account(self.data.get("account_id"))
        if not account.is_closed:
            raise UndoError("счёт уже открыт")
        AccountRepository.update(account, is_closed=False)


class TransferCommand(Command):
    action_type = ACTION_TRANSFER

    def undo(self) -> None:
        sender = self._account(self.data.get("from_id"), "счёт списания")
        receiver = self._account(self.data.get("to_id"), "счёт получателя")
        amount = float(self.data.get("amount", 0))
        if receiver.balance < amount:
            raise UndoError("у получателя уже нет этих средств — отмена невозможна")
        # возвращаем деньги: у получателя списываем, отправителю зачисляем
        AccountRepository.move_funds(receiver, sender, amount)


class SalaryCommand(Command):
    action_type = ACTION_SALARY

    def undo(self) -> None:
        account = self._account(self.data.get("account_id"))
        amount = float(self.data.get("amount", 0))
        if account.balance < amount:
            raise UndoError("на счёте уже нет суммы выплаты — отмена невозможна")
        AccountRepository.add_balance(account, -amount)
        request = SalaryRequestRepository.get_by_id(self.data.get("request_id"))
        if request is not None:
            SalaryRequestRepository.update(request, last_paid_at=None)


class AccumulateCommand(Command):
    action_type = ACTION_ACCUMULATE

    def undo(self) -> None:
        items = self.data.get("items") or []
        if not items:
            raise UndoError("в записи нет данных о начислении")
        prepared = []
        for item in items:
            account = self._account(item.get("account_id"))
            bonus = float(item.get("bonus", 0))
            if account.balance < bonus:
                raise UndoError(f"на счёте №{account.id} уже нет начисленной суммы")
            prepared.append((account, bonus))
        for account, bonus in prepared:
            AccountRepository.add_balance(account, -bonus)


class ApproveUserCommand(Command):
    action_type = ACTION_APPROVE_USER

    def undo(self) -> None:
        user = UserRepository.get_by_id(self.data.get("user_id"))
        if user is None:
            raise UndoError("пользователь не найден")
        if not user.is_approved:
            raise UndoError("регистрация уже не подтверждена")
        UserRepository.set_approved(user, False)


class RejectUserCommand(Command):
    action_type = ACTION_REJECT_USER

    def undo(self) -> None:
        user = UserRepository.get_by_id(self.data.get("user_id"))
        if user is None:
            raise UndoError("пользователь не найден")
        if not user.is_rejected:
            raise UndoError("регистрация уже не отклонена")
        UserRepository.update_rejected(user, False)


class ApplySalaryCommand(Command):
    action_type = ACTION_APPLY_SALARY

    def undo(self) -> None:
        request = SalaryRequestRepository.get_by_id(self.data.get("request_id"))
        if request is None:
            raise UndoError("заявка не найдена")
        if request.status != REQ_PENDING:
            raise UndoError("заявка уже рассмотрена — сначала отмените решение менеджера")
        SalaryRequestRepository.delete(request)


class ApproveSalaryCommand(Command):
    action_type = ACTION_APPROVE_SALARY

    def undo(self) -> None:
        request = SalaryRequestRepository.get_by_id(self.data.get("request_id"))
        if request is None:
            raise UndoError("заявка не найдена")
        if not self.data.get("employment_created", True):
            employment = EmploymentRepository.get(request.user_id, request.enterprise_id)
            if employment is not None and self.data.get("previous_salary") is not None:
                EmploymentRepository.update_salary(employment, self.data["previous_salary"])
        else:
            employment = EmploymentRepository.get(request.user_id, request.enterprise_id)
            if employment is not None:
                EmploymentRepository.remove(employment)
        SalaryRequestRepository.update(request, status=REQ_PENDING)


class RejectSalaryCommand(Command):
    action_type = ACTION_REJECT_SALARY

    def undo(self) -> None:
        request = SalaryRequestRepository.get_by_id(self.data.get("request_id"))
        if request is None:
            raise UndoError("заявка не найдена")
        SalaryRequestRepository.update(request, status=REQ_PENDING)


class RevokeSalaryCommand(Command):
    action_type = ACTION_REVOKE_SALARY

    def undo(self) -> None:
        request = SalaryRequestRepository.get_by_id(self.data.get("request_id"))
        if request is None:
            raise UndoError("заявка не найдена")
        if request.status != REQ_PENDING:
            raise UndoError("заявка уже не в состоянии «ожидает решения»")
        SalaryRequestRepository.update(request, status=REQ_APPROVED)
        if EmploymentRepository.get(request.user_id, request.enterprise_id) is None:
            EmploymentRepository.add(
                request.user_id, request.enterprise_id, self.data.get("salary_amount", 1000.0),
            )


class FireEmployeeCommand(Command):
    action_type = ACTION_FIRE_EMPLOYEE

    def undo(self) -> None:
        user_id = self.data.get("user_id")
        enterprise_id = self.data.get("enterprise_id")
        if EmploymentRepository.get(user_id, enterprise_id) is not None:
            raise UndoError("сотрудник уже восстановлен")
        EmploymentRepository.add(user_id, enterprise_id, self.data.get("salary_amount", 1000.0))


class BlockCommand(Command):
    action_type = ACTION_BLOCK

    def undo(self) -> None:
        account = self._account(self.data.get("account_id"))
        AccountRepository.update(account, is_blocked=bool(self.data.get("previous", False)))


class UnblockCommand(Command):
    action_type = ACTION_UNBLOCK

    def undo(self) -> None:
        account = self._account(self.data.get("account_id"))
        AccountRepository.update(account, is_blocked=bool(self.data.get("previous", True)))


COMMANDS = {
    command.action_type: command
    for command in (
        OpenAccountCommand,
        CloseAccountCommand,
        TransferCommand,
        SalaryCommand,
        AccumulateCommand,
        ApproveUserCommand,
        RejectUserCommand,
        ApplySalaryCommand,
        ApproveSalaryCommand,
        RejectSalaryCommand,
        RevokeSalaryCommand,
        FireEmployeeCommand,
        BlockCommand,
        UnblockCommand,
    )
}

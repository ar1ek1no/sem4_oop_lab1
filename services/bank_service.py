"""Операции клиента: счета, вклады, переводы, зарплата, история.

Каждая операция начинается с проверки прав: счёт должен принадлежать текущему
пользователю (NFR-5), быть открытым и (для списания) не заблокированным.
"""
from models import (
    ACCOUNT_TYPES,
    ACTION_ACCUMULATE,
    ACTION_APPLY_SALARY,
    ACTION_CLOSE_ACCOUNT,
    ACTION_OPEN_ACCOUNT,
    ACTION_SALARY,
    ACTION_TRANSFER,
    DEPOSIT_RATE,
    utcnow,
)
from repositories.account_repository import AccountRepository
from repositories.bank_repository import BankRepository
from repositories.employment_repository import EmploymentRepository
from repositories.enterprise_repository import EnterpriseRepository
from repositories.log_repository import LogRepository
from repositories.salary_repository import SalaryRequestRepository
from services.validators import check_amount_value


class BankService:
    # --- счета и вклады -------------------------------------------------
    @staticmethod
    def open_account(user_id: int, bank_id: int, acc_type: str) -> tuple[bool, str]:
        if acc_type not in ACCOUNT_TYPES:
            return False, "неизвестный тип счёта"
        bank = BankRepository.get_by_id(bank_id)
        if bank is None:
            return False, "банк не найден"
        account = AccountRepository.create(user_id, bank.id, acc_type)
        LogRepository.create(
            ACTION_OPEN_ACCOUNT,
            receiver_acc_id=account.id,
            actor_id=user_id,
            payload={"account_id": account.id, "user_id": user_id, "bank_id": bank.id,
                     "acc_type": acc_type},
        )
        return True, f"открыт {account.type_title} №{account.id} в банке {bank.name}"

    @staticmethod
    def close_account(user_id: int, account_id: int) -> tuple[bool, str]:
        account = AccountRepository.get_for_user(account_id, user_id)
        if account is None:
            return False, "счёт не найден"
        if account.is_closed:
            return False, "счёт уже закрыт"
        if account.is_blocked:
            return False, "счёт заблокирован — закрытие недоступно"
        if abs(account.balance) > 0.001:
            return False, "закрыть можно только счёт с нулевым балансом"
        AccountRepository.update(account, is_closed=True)
        LogRepository.create(
            ACTION_CLOSE_ACCOUNT,
            receiver_acc_id=account.id,
            actor_id=user_id,
            payload={"account_id": account.id, "user_id": user_id},
        )
        return True, f"счёт №{account.id} закрыт"

    # --- переводы --------------------------------------------------------
    @staticmethod
    def transfer(user_id: int, from_id: int, to_id: int, amount: float) -> tuple[bool, str]:
        error = check_amount_value(amount)
        if error:
            return False, error
        amount = round(float(amount), 2)
        if from_id == to_id:
            return False, "нельзя перевести на тот же счёт"
        sender = AccountRepository.get_for_user(from_id, user_id)
        if sender is None:
            return False, "счёт списания не найден"
        if sender.is_closed:
            return False, "счёт списания закрыт"
        if sender.is_blocked:
            return False, "счёт списания заблокирован"
        receiver = AccountRepository.get_by_id(to_id)
        if receiver is None:
            return False, "счёт получателя не найден"
        if receiver.is_closed:
            return False, "счёт получателя закрыт"
        if receiver.is_blocked:
            return False, "счёт получателя заблокирован"
        if sender.balance < amount:
            return False, "недостаточно средств на счёте списания"

        AccountRepository.move_funds(sender, receiver, amount)
        LogRepository.create(
            ACTION_TRANSFER,
            amount=amount,
            sender_acc_id=sender.id,
            receiver_acc_id=receiver.id,
            actor_id=user_id,
            payload={"from_id": sender.id, "to_id": receiver.id, "amount": amount,
                     "user_id": user_id},
        )
        return True, f"перевод {amount:.2f} BYN выполнен"

    # --- вклады ----------------------------------------------------------
    @staticmethod
    def accumulate(user_id: int) -> tuple[bool, str]:
        """Начисление процента на вклады. Заблокированные и закрытые не участвуют (FR-11)."""
        accounts = [
            account
            for account in AccountRepository.get_user_accounts(user_id)
            if account.is_saving and not account.is_blocked and account.balance > 0
        ]
        if not accounts:
            return False, "нет вкладов с положительным балансом"

        items = []
        for account in accounts:
            bonus = round(account.balance * DEPOSIT_RATE, 2)
            if bonus <= 0:
                continue
            AccountRepository.add_balance(account, bonus)
            items.append({"account_id": account.id, "bonus": bonus})
        if not items:
            return False, "начислять нечего: суммы на вкладах слишком малы"

        LogRepository.create(
            ACTION_ACCUMULATE,
            amount=round(sum(item["bonus"] for item in items), 2),
            actor_id=user_id,
            payload={"items": items, "user_id": user_id},
        )
        return True, f"начислено {int(DEPOSIT_RATE * 100)} % на {len(items)} вклад(ов)"

    # --- зарплатный проект ----------------------------------------------
    @staticmethod
    def apply_for_salary(user_id: int, enterprise_id: int) -> tuple[bool, str]:
        enterprise = EnterpriseRepository.get_by_id(enterprise_id)
        if enterprise is None:
            return False, "предприятие не найдено"
        if SalaryRequestRepository.get_active(user_id, enterprise_id) is not None:
            return False, "заявка уже подана и ожидает решения или действует"
        request = SalaryRequestRepository.create(user_id, enterprise.id)
        LogRepository.create(
            ACTION_APPLY_SALARY,
            actor_id=user_id,
            payload={"request_id": request.id, "user_id": user_id,
                     "enterprise_id": enterprise.id},
        )
        return True, f"заявка на зарплатный проект «{enterprise.name}» отправлена менеджеру"

    @staticmethod
    def pay_salary(user_id: int, enterprise_id: int, account_id: int) -> tuple[bool, str]:
        """Выплата возможна только по подтверждённой заявке и раз в расчётный период."""
        employment = EmploymentRepository.get(user_id, enterprise_id)
        if employment is None:
            return False, "вы не являетесь сотрудником этого предприятия"
        request = SalaryRequestRepository.get_approved(user_id, enterprise_id)
        if request is None:
            return False, "нет подтверждённой заявки на этот зарплатный проект"
        if request.last_paid_at is not None and BankService._same_period(request.last_paid_at):
            return False, "зарплата за текущий период уже выплачена"

        account = AccountRepository.get_for_user(account_id, user_id)
        if account is None:
            return False, "счёт не найден"
        if account.is_closed:
            return False, "счёт закрыт"
        if account.is_blocked:
            return False, "счёт заблокирован — выберите другой"

        amount = round(float(employment.salary_amount), 2)
        AccountRepository.add_balance(account, amount)
        SalaryRequestRepository.update(request, last_paid_at=utcnow())
        LogRepository.create(
            ACTION_SALARY,
            amount=amount,
            receiver_acc_id=account.id,
            actor_id=user_id,
            payload={"request_id": request.id, "account_id": account.id, "amount": amount,
                     "user_id": user_id, "enterprise_id": enterprise_id},
        )
        return True, f"зарплата {amount:.2f} BYN зачислена на счёт №{account.id}"

    @staticmethod
    def _same_period(moment) -> bool:
        now = utcnow()
        return (moment.year, moment.month) == (now.year, now.month)

    # --- история ---------------------------------------------------------
    @staticmethod
    def history(user_id: int) -> list:
        """История по всем счетам, включая закрытые: закрытие не стирает историю."""
        account_ids = [account.id for account in AccountRepository.get_user_accounts(
            user_id, include_closed=True)]
        return LogRepository.get_for_accounts(account_ids)

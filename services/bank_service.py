from models import session, Account, TransactionLog, SalaryRequest, Employment
from repositories.account_repository import AccountRepository


class BankService:
    @staticmethod
    def open_account(user_id, bank_id, acc_type):
        new_acc = Account(user_id=user_id, bank_id=bank_id, acc_type=acc_type, balance=0.0)
        session.add(new_acc)
        session.flush()  # Получаем ID
        log = TransactionLog(receiver_acc_id=new_acc.id, amount=0.0, action_type='open_acc')
        session.add(log)
        session.commit()

    @staticmethod
    def transfer_money(from_id, to_id, amount):
        if amount <= 0: return False, "сумма перевода должна быть > 0"

        sender = session.query(Account).get(from_id)
        receiver = session.query(Account).get(to_id)

        if not sender or not receiver: return False, "счет не найден"
        if sender.is_blocked: return False, "ваш счет заблокирован"
        if sender.balance < amount: return False, "недостаточно средств (u too confident about your savings blud)"

        sender.balance -= amount
        receiver.balance += amount

        log = TransactionLog(sender_acc_id=from_id, receiver_acc_id=to_id, amount=amount, action_type='transfer')
        session.add(log)
        session.commit()
        return True, "перевод выполнен"

    @staticmethod
    def apply_for_salary(user_id, enterprise_id):
        existing = session.query(SalaryRequest).filter_by(user_id=user_id, enterprise_id=enterprise_id).first()
        if existing: return False, "заявка уже подана"

        req = SalaryRequest(user_id=user_id, enterprise_id=enterprise_id)
        session.add(req)
        session.commit()
        return True, "заявка подана, ждем вашу allowance!"

    @staticmethod
    def get_salary(user_id, enterprise_id, target_acc_id):
        emp = session.query(Employment).filter_by(user_id=user_id, enterprise_id=enterprise_id).first()
        if not emp:
            return False, "вы не являетесь сотрудником этой компании"

        acc = session.query(Account).get(target_acc_id)
        if not acc or acc.is_blocked: return False, "cчет заблокирован"

        salary_amount = 1000.0
        acc.balance += salary_amount

        log = TransactionLog(receiver_acc_id=target_acc_id, amount=salary_amount, action_type='salary')
        session.add(log)
        session.commit()
        return True, f"зарплата {salary_amount} BYN зачислена!"

    @staticmethod
    def accumulate_savings(user_id):
        accs = session.query(Account).filter_by(user_id=user_id, acc_type='saving', is_blocked=False).all()
        count = 0
        for a in accs:
            if a.balance > 0:
                bonus = a.balance * 0.05
                a.balance += bonus
                count += 1
        session.commit()
        return True, f"начислено 5% на {count} вклада(ов) (you should fear inflation twin)"

    @staticmethod
    def get_history(user_id):
        # по id счетов юзера
        user_acc_ids = [a.id for a in AccountRepository.get_user_accounts(user_id)]
        return session.query(TransactionLog).filter(
            (TransactionLog.sender_acc_id.in_(user_acc_ids)) |
            (TransactionLog.receiver_acc_id.in_(user_acc_ids))
        ).order_by(TransactionLog.timestamp.desc()).all()

    @staticmethod
    def close_account(acc_id):
        acc = session.query(Account).get(acc_id)
        if acc and acc.balance == 0:
            session.delete(acc)
            session.commit()
            return True, "счет закрыт"
        return False, "баланс должен быть 0 (last chance..)"

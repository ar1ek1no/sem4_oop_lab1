from models import session, Account

class AccountRepository:
    @staticmethod
    def create_account(user_id: int, bank_id: int, acc_type: str):
        new_account = Account(
            user_id=user_id,
            bank_id=bank_id,
            acc_type=acc_type,
            balance=0.0
        )
        session.add(new_account)
        session.commit()
        return new_account

    @staticmethod
    def get_user_accounts(user_id: int):
        return session.query(Account).filter(Account.user_id == user_id).all()

    @staticmethod
    def get_account_by_id(acc_id: int):
        return session.query(Account).filter(Account.id == acc_id).first()

    @staticmethod
    def change_balance(acc_id: int, amount: float):
        account = session.query(Account).get(acc_id)
        if account:
            account.balance += amount
            session.commit()
            return True
        return False

    @staticmethod
    def set_block_status(acc_id: int, is_blocked: bool):
        account = session.query(Account).get(acc_id)
        if account: # менеджер изменяет
            account.is_blocked = is_blocked
            session.commit()
            return True
        return False
    @staticmethod
    def delete_account(acc_id):
        acc = session.query(Account).get(acc_id)
        if acc:
            session.delete(acc)
            session.commit()
            return True
        return False

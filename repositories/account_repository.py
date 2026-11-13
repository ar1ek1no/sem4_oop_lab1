"""Репозиторий счетов."""
from extensions import db
from models import ACC_CHECKING, Account


class AccountRepository:
    @staticmethod
    def create(user_id: int, bank_id: int, acc_type: str = ACC_CHECKING) -> Account:
        account = Account(user_id=user_id, bank_id=bank_id, acc_type=acc_type, balance=0.0)
        db.session.add(account)
        db.session.commit()
        return account

    @staticmethod
    def get_by_id(account_id: int) -> Account | None:
        return db.session.get(Account, account_id)

    @staticmethod
    def get_for_user(account_id: int, user_id: int) -> Account | None:
        """Счёт пользователя: единственный способ получить «свой» счёт (NFR-5)."""
        return (
            db.session.query(Account)
            .filter(Account.id == account_id, Account.user_id == user_id)
            .first()
        )

    @staticmethod
    def get_user_accounts(user_id: int, include_closed: bool = False) -> list[Account]:
        query = db.session.query(Account).filter(Account.user_id == user_id)
        if not include_closed:
            query = query.filter(Account.is_closed.is_(False))
        return query.order_by(Account.id).all()

    @staticmethod
    def get_all() -> list[Account]:
        return db.session.query(Account).order_by(Account.id).all()

    @staticmethod
    def update(account: Account, **fields) -> Account:
        for name, value in fields.items():
            setattr(account, name, value)
        db.session.commit()
        return account

    @staticmethod
    def add_balance(account: Account, delta: float) -> Account:
        account.balance = round(account.balance + delta, 2)
        db.session.commit()
        return account

    @staticmethod
    def move_funds(sender: Account, receiver: Account, amount: float) -> None:
        """Списание и зачисление одной транзакцией: половинчатого перевода быть не должно."""
        sender.balance = round(sender.balance - amount, 2)
        receiver.balance = round(receiver.balance + amount, 2)
        db.session.commit()

    @staticmethod
    def delete(account: Account) -> None:
        db.session.delete(account)
        db.session.commit()

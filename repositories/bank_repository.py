"""Репозиторий банков."""
from extensions import db
from models import Bank


class BankRepository:
    """Репозиторий — не наследник модели (ISSUE-6): только запросы."""

    @staticmethod
    def get_all() -> list[Bank]:
        return db.session.query(Bank).order_by(Bank.name).all()

    @staticmethod
    def get_by_id(bank_id: int) -> Bank | None:
        return db.session.get(Bank, bank_id)

    @staticmethod
    def get_by_name(name: str) -> Bank | None:
        return db.session.query(Bank).filter(Bank.name == name).first()

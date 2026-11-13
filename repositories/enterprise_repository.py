"""Репозиторий предприятий."""
from extensions import db
from models import Enterprise


class EnterpriseRepository:
    @staticmethod
    def get_all() -> list[Enterprise]:
        return db.session.query(Enterprise).order_by(Enterprise.name).all()

    @staticmethod
    def get_by_id(enterprise_id: int) -> Enterprise | None:
        return db.session.get(Enterprise, enterprise_id)

    @staticmethod
    def get_by_name(name: str) -> Enterprise | None:
        return db.session.query(Enterprise).filter(Enterprise.name == name).first()

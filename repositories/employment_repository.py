"""Репозиторий трудоустройства: кто в каком предприятии и с каким окладом."""
from extensions import db
from models import Employment


class EmploymentRepository:
    @staticmethod
    def get(user_id: int, enterprise_id: int) -> Employment | None:
        return (
            db.session.query(Employment)
            .filter(Employment.user_id == user_id, Employment.enterprise_id == enterprise_id)
            .first()
        )

    @staticmethod
    def get_for_enterprise(enterprise_id: int) -> list[Employment]:
        return (
            db.session.query(Employment)
            .filter(Employment.enterprise_id == enterprise_id)
            .all()
        )

    @staticmethod
    def get_for_user(user_id: int) -> list[Employment]:
        return db.session.query(Employment).filter(Employment.user_id == user_id).all()

    @staticmethod
    def add(user_id: int, enterprise_id: int, salary_amount: float) -> Employment:
        employment = Employment(
            user_id=user_id, enterprise_id=enterprise_id, salary_amount=salary_amount,
        )
        db.session.add(employment)
        db.session.commit()
        return employment

    @staticmethod
    def remove(employment: Employment) -> None:
        db.session.delete(employment)
        db.session.commit()

    @staticmethod
    def update_salary(employment: Employment, salary_amount: float) -> Employment:
        employment.salary_amount = salary_amount
        db.session.commit()
        return employment

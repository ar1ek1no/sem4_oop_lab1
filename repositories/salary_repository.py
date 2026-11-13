"""Репозиторий заявок на зарплатный проект."""
from extensions import db
from models import REQ_APPROVED, REQ_PENDING, SalaryRequest


class SalaryRequestRepository:
    @staticmethod
    def create(user_id: int, enterprise_id: int) -> SalaryRequest:
        request = SalaryRequest(user_id=user_id, enterprise_id=enterprise_id, status=REQ_PENDING)
        db.session.add(request)
        db.session.commit()
        return request

    @staticmethod
    def get_by_id(request_id: int) -> SalaryRequest | None:
        return db.session.get(SalaryRequest, request_id)

    @staticmethod
    def get_active(user_id: int, enterprise_id: int) -> SalaryRequest | None:
        """Незакрытая заявка: ожидает решения или подтверждена (FR-12)."""
        return (
            db.session.query(SalaryRequest)
            .filter(
                SalaryRequest.user_id == user_id,
                SalaryRequest.enterprise_id == enterprise_id,
                SalaryRequest.status.in_((REQ_PENDING, REQ_APPROVED)),
            )
            .first()
        )

    @staticmethod
    def get_approved(user_id: int, enterprise_id: int) -> SalaryRequest | None:
        return (
            db.session.query(SalaryRequest)
            .filter(
                SalaryRequest.user_id == user_id,
                SalaryRequest.enterprise_id == enterprise_id,
                SalaryRequest.status == REQ_APPROVED,
            )
            .first()
        )

    @staticmethod
    def get_pending() -> list[SalaryRequest]:
        return (
            db.session.query(SalaryRequest)
            .filter(SalaryRequest.status == REQ_PENDING)
            .order_by(SalaryRequest.created_at)
            .all()
        )

    @staticmethod
    def get_for_user(user_id: int) -> list[SalaryRequest]:
        return (
            db.session.query(SalaryRequest)
            .filter(SalaryRequest.user_id == user_id)
            .order_by(SalaryRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def get_all() -> list[SalaryRequest]:
        return (
            db.session.query(SalaryRequest)
            .order_by(SalaryRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def update(request: SalaryRequest, **fields) -> SalaryRequest:
        for name, value in fields.items():
            setattr(request, name, value)
        db.session.commit()
        return request

    @staticmethod
    def delete(request: SalaryRequest) -> None:
        db.session.delete(request)
        db.session.commit()

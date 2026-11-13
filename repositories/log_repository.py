"""Репозиторий журнала действий.

Журнал — единственный источник истории и для клиента, и для отмены администратором.
"""
from extensions import db
from models import LOG_CANCELLED, LOG_COMPLETED, TransactionLog


class LogRepository:
    @staticmethod
    def create(
        action_type: str,
        amount: float = 0.0,
        sender_acc_id: int | None = None,
        receiver_acc_id: int | None = None,
        actor_id: int | None = None,
        payload: dict | None = None,
    ) -> TransactionLog:
        log = TransactionLog(
            action_type=action_type,
            amount=amount,
            sender_acc_id=sender_acc_id,
            receiver_acc_id=receiver_acc_id,
            actor_id=actor_id,
            payload=payload or {},
            status=LOG_COMPLETED,
        )
        db.session.add(log)
        db.session.commit()
        return log

    @staticmethod
    def get_by_id(log_id: int) -> TransactionLog | None:
        return db.session.get(TransactionLog, log_id)

    @staticmethod
    def get_all(limit: int | None = None) -> list[TransactionLog]:
        query = db.session.query(TransactionLog).order_by(TransactionLog.timestamp.desc(),
                                                          TransactionLog.id.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def get_for_accounts(account_ids: list[int], limit: int | None = None) -> list[TransactionLog]:
        if not account_ids:
            return []
        query = (
            db.session.query(TransactionLog)
            .filter(
                (TransactionLog.sender_acc_id.in_(account_ids))
                | (TransactionLog.receiver_acc_id.in_(account_ids)),
            )
            .order_by(TransactionLog.timestamp.desc(), TransactionLog.id.desc())
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def mark_cancelled(log: TransactionLog) -> None:
        log.status = LOG_CANCELLED
        db.session.commit()

    @staticmethod
    def rollback() -> None:
        """Откат незавершённой операции (используется отменой действия)."""
        db.session.rollback()

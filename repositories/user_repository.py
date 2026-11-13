"""Репозиторий пользователей: только доступ к данным, без бизнес-правил."""
from extensions import db
from models import ROLE_CLIENT, User


class UserRepository:
    @staticmethod
    def create(username: str, password_hash: str, full_name: str, role: str = ROLE_CLIENT,
               is_approved: bool = False) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_approved=is_approved,
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def get_by_username(username: str) -> User | None:
        return db.session.query(User).filter(User.username == username).first()

    @staticmethod
    def get_by_id(user_id: int) -> User | None:
        return db.session.get(User, user_id)

    @staticmethod
    def get_pending_clients() -> list[User]:
        """Клиенты, ожидающие подтверждения менеджером (FR-3). Отклонённые не попадают."""
        return (
            db.session.query(User)
            .filter(
                User.role == ROLE_CLIENT,
                User.is_approved.is_(False),
                User.is_rejected.is_(False),
            )
            .order_by(User.created_at)
            .all()
        )

    @staticmethod
    def approve(user: User) -> None:
        user.is_approved = True
        db.session.commit()

    @staticmethod
    def set_approved(user: User, approved: bool) -> None:
        user.is_approved = approved
        db.session.commit()

    @staticmethod
    def reject(user: User) -> None:
        """Отклонённая регистрация остаётся в БД: отмену можно откатить (FR-15)."""
        user.is_rejected = True
        db.session.commit()

    @staticmethod
    def update_rejected(user: User, rejected: bool) -> None:
        user.is_rejected = rejected
        db.session.commit()

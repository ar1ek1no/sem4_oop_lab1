"""Аутентификация и регистрация.

Правила, которые здесь закреплены:
- публичная регистрация создаёт **только клиента** (ISSUE-2);
- пароль хранится хэшем, сравнение — по хэшу (ISSUE-1, NFR-2);
- неподтверждённая или отклонённая учётная запись не пускает в систему (FR-2, FR-3);
- «текущий пользователь» — не поле сервиса, а сессия Flask (ISSUE-7).
"""
from werkzeug.security import check_password_hash, generate_password_hash

from models import ROLE_CLIENT
from repositories.user_repository import UserRepository
from services.validators import check_full_name, check_password, check_username

# Хэш-пустышка: сравнение выполняется даже для несуществующего логина,
# чтобы по времени ответа нельзя было понять, есть такой пользователь или нет.
_DUMMY_HASH = generate_password_hash("dummy-password-for-timing")


class AuthService:
    @staticmethod
    def register(username: str, password: str, full_name: str) -> tuple[bool, str]:
        """Регистрирует клиента. Роль не принимается из формы — только `client`."""
        username = (username or "").strip()
        full_name = (full_name or "").strip()
        for error in (check_username(username), check_password(password), check_full_name(full_name)):
            if error:
                return False, error
        if UserRepository.get_by_username(username):
            return False, "такой логин уже занят"
        UserRepository.create(
            username=username,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            role=ROLE_CLIENT,
            is_approved=False,
        )
        return True, "заявка отправлена: менеджер должен подтвердить регистрацию"

    @staticmethod
    def authenticate(username: str, password: str) -> tuple[bool, str, object | None]:
        """Проверяет пару логин/пароль и право входа."""
        user = UserRepository.get_by_username((username or "").strip())
        password = password or ""
        if user is None:
            check_password_hash(_DUMMY_HASH, password)
            return False, "неверный логин или пароль", None
        if not check_password_hash(user.password_hash, password):
            return False, "неверный логин или пароль", None
        if user.is_rejected:
            return False, "заявка на регистрацию отклонена менеджером", None
        if not user.is_approved:
            return False, "учётная запись ещё не подтверждена менеджером", None
        return True, "вход выполнен", user

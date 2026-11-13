"""Общие помощники веб-слоя: текущий пользователь, проверки ролей, разбор формы."""
from functools import wraps

from flask import abort, current_app, flash, g, redirect, request, session, url_for

from extensions import db
from models import ROLE_ADMIN, ROLE_CLIENT, ROLE_MANAGER, User


def load_current_user() -> None:
    """Кладёт пользователя из сессии в `g`. Сессия — единственный источник «кто я»."""
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id else None
    if user_id and g.user is None:
        session.clear()


def login_user(user: User) -> None:
    session.clear()
    session["user_id"] = user.id
    session.permanent = True


def logout_user() -> None:
    session.clear()


def _login_redirect():
    target = request.full_path if request.query_string else request.path
    flash("сначала войдите в систему", "warning")
    return redirect(url_for("auth.login", next=target))


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return _login_redirect()
        return view(*args, **kwargs)

    return wrapper


def role_required(*roles: str):
    """Проверка роли: сначала вход, потом право (403, а не 404 — роль известна)."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if g.user is None:
                return _login_redirect()
            if g.user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator


def client_required(view):
    return role_required(ROLE_CLIENT)(view)


def manager_required(view):
    return role_required(ROLE_MANAGER)(view)


def admin_required(view):
    return role_required(ROLE_ADMIN)(view)


def flash_result(ok: bool, message: str) -> None:
    flash(message, "success" if ok else "error")


def audit(message: str) -> None:
    """Значимое действие — в файл (NFR-4). Журнал в БД ведут сервисы."""
    user = getattr(g, "user", None)
    who = f"user={user.username} role={user.role}" if user else "user=anonymous"
    current_app.logger.info("%s %s", who, message)


def form_value(name: str, default: str = "") -> str:
    return (request.form.get(name) or default).strip()


def form_int(name: str) -> int | None:
    raw = form_value(name)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def form_float(name: str) -> float | None:
    raw = form_value(name).replace(",", ".")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None

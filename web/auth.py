"""Вход, регистрация, выход."""
from urllib.parse import urlparse

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from services.auth_service import AuthService
from services.validators import check_full_name, check_password, check_username
from web.helpers import audit, flash_result, form_value, login_user, logout_user

bp = Blueprint("auth", __name__)


def _safe_next(target: str | None) -> str | None:
    """Открытый редирект — дыра: пускаем только относительные пути этого же сайта."""
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = form_value("username")
        ok, message, user = AuthService.authenticate(username, request.form.get("password", ""))
        if ok:
            login_user(user)
            audit(f"вход выполнен: {user.username} ({user.role})")
            return redirect(_safe_next(request.args.get("next")) or url_for("index"))
        audit(f"неудачный вход: {username!r}")
        flash_result(ok, message)
    return render_template("auth/login.html", next=request.args.get("next", ""))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for("index"))

    errors: dict[str, str] = {}
    if request.method == "POST":
        username = form_value("username")
        password = request.form.get("password", "")
        full_name = form_value("full_name")

        # показываем ошибку рядом с полем, но проверяем всё равно в сервисе
        for field, error in (
            ("username", check_username(username)),
            ("password", check_password(password)),
            ("full_name", check_full_name(full_name)),
        ):
            if error:
                errors[field] = error
        if not errors:
            ok, message = AuthService.register(username, password, full_name)
            flash_result(ok, message)
            audit(f"регистрация: {username!r} — {message}")
            if ok:
                return redirect(url_for("auth.login"))
            errors["username"] = message
    return render_template("auth/register.html", errors=errors)


@bp.post("/logout")
def logout():
    if g.user is not None:
        audit(f"выход: {g.user.username}")
    logout_user()
    flash("вы вышли из системы", "info")
    return redirect(url_for("auth.login"))


@bp.get("/logout")
def logout_get():
    """Ссылка в навигации; действие идемпотентно, но POST предпочтительнее."""
    return logout()

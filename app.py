"""Точка сборки приложения.

`flask --app app run` подхватывает фабрику `create_app`.
"""
import logging

from flask import Flask, g, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException

from config import Config
from db_migrate import migrate_legacy_schema
from extensions import db
from logging_setup import configure_logging
from models import ACCOUNT_TYPE_TITLES, REQUEST_STATUS_TITLES, ROLE_ADMIN, ROLE_CLIENT, ROLE_MANAGER
from services.validators import format_money
from web.admin import bp as admin_bp
from web.api import bp as api_bp
from web.auth import bp as auth_bp
from web.client import bp as client_bp
from web.helpers import load_current_user
from web.manager import bp as manager_bp

HTTP_ERROR_MESSAGES = {
    400: "неверный запрос: проверьте переданные данные",
    401: "для этого действия нужно войти в систему",
    403: "у вашей роли нет прав на это действие",
    404: "страница или объект не найдены",
    405: "такой метод запроса не поддерживается",
}


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.ensure_ascii = False  # кириллица в JSON без \u-escape
    configure_logging(app)
    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    app.before_request(load_current_user)
    app.jinja_env.filters["money"] = format_money
    app.jinja_env.globals.update(
        ACCOUNT_TYPE_TITLES=ACCOUNT_TYPE_TITLES,
        REQUEST_STATUS_TITLES=REQUEST_STATUS_TITLES,
    )

    @app.route("/")
    def index():
        if g.user is None:
            return redirect(url_for("auth.login"))
        return redirect(_home_by_role(g.user.role))

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        status = error.code or 500
        # своё описание из abort(description=...) важнее стандартного английского
        default = type(error).description
        message = error.description if error.description and error.description != default else None
        message = message or HTTP_ERROR_MESSAGES.get(status, "ошибка запроса")
        if _wants_json():
            return jsonify({"error": message, "status": status}), status
        template = {400: "errors/400.html", 401: "errors/401.html",
                    403: "errors/403.html", 404: "errors/404.html"}.get(status)
        if template is None:
            return render_template("errors/generic.html", status=status, message=message), status
        return render_template(template, message=message), status

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Необработанная ошибка: %s", error)
        if _wants_json():
            return jsonify({"error": "внутренняя ошибка сервера", "status": 500}), 500
        return render_template("errors/500.html", message="внутренняя ошибка сервера"), 500

    with app.app_context():
        db.create_all()
        migrate_legacy_schema(db.engine, app.logger)

    app.logger.info("Приложение собрано: %s", app.config["SQLALCHEMY_DATABASE_URI"])
    return app


def _home_by_role(role: str) -> str:
    if role == ROLE_CLIENT:
        return url_for("client.accounts")
    if role == ROLE_MANAGER:
        return url_for("manager.clients")
    if role == ROLE_ADMIN:
        return url_for("admin.logs")
    return url_for("auth.login")


def _wants_json() -> bool:
    """Ошибки API отдаются JSON-ом, ошибки страниц — HTML-ом (NFR-3, ЛР4)."""
    if request.path.startswith("/api/"):
        return True
    return request.accept_mimetypes.best == "application/json"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(debug=True)

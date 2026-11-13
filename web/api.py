"""JSON API `/api/v1` — для Postman и нагрузочных прогонов (FR-16).

Авторизация: токен, выданный `/api/v1/login`, передаётся заголовком
`Authorization: Bearer <token>`. Куки не используются, поэтому запросы
связываются между собой именно токеном (требование ЛР4).
"""
from functools import wraps

from flask import Blueprint, abort, current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from extensions import db
from models import ACC_CHECKING, ACC_SAVING, ROLE_ADMIN, ROLE_CLIENT, ROLE_MANAGER, User
from repositories.account_repository import AccountRepository
from repositories.bank_repository import BankRepository
from repositories.enterprise_repository import EnterpriseRepository
from repositories.salary_repository import SalaryRequestRepository
from services.admin_service import AdminService
from services.auth_service import AuthService
from services.bank_service import BankService
from services.manager_service import ManagerService
from services.validators import check_amount_value, format_money, parse_amount

bp = Blueprint("api", __name__, url_prefix="/api/v1")

TOKEN_TTL_SECONDS = 8 * 60 * 60
TOKEN_SALT = "api-token"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=TOKEN_SALT)


def issue_token(user: User) -> str:
    return _serializer().dumps({"uid": user.id})


def _authenticate():
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None, (jsonify({"error": "нужен заголовок Authorization: Bearer <token>",
                               "status": 401}), 401)
    token = header.split(" ", 1)[1].strip()
    try:
        data = _serializer().loads(token, max_age=TOKEN_TTL_SECONDS)
    except SignatureExpired:
        return None, (jsonify({"error": "токен истёк — войдите заново", "status": 401}), 401)
    except BadSignature:
        return None, (jsonify({"error": "неверный токен", "status": 401}), 401)

    user = db.session.get(User, data.get("uid"))
    if user is None or user.is_rejected or not user.is_approved:
        return None, (jsonify({"error": "пользователь не может работать в системе",
                               "status": 401}), 401)
    return user, None


def api_auth(*roles: str):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user, error = _authenticate()
            if error is not None:
                return error
            if roles and user.role not in roles:
                return jsonify({"error": "недостаточно прав", "status": 403}), 403
            g.api_user = user
            return view(*args, **kwargs)

        return wrapper

    return decorator


def _json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="тело запроса должно быть JSON-объектом")
    return data


def _amount(value) -> tuple[float | None, str | None]:
    amount, error = parse_amount(value)
    if error:
        return None, error
    return amount, None


def _user_view(user: User) -> dict:
    return {"id": user.id, "username": user.username, "full_name": user.full_name,
            "role": user.role}


def _account_view(account) -> dict:
    return {"id": account.id, "bank_id": account.bank_id,
            "bank": account.bank.name if account.bank else None,
            "type": account.acc_type, "balance": account.balance,
            "balance_text": format_money(account.balance),
            "blocked": account.is_blocked, "closed": account.is_closed}


def _log_view(log) -> dict:
    return {"id": log.id, "action": log.action_type, "action_title": log.action_title,
            "amount": log.amount, "sender_account_id": log.sender_acc_id,
            "receiver_account_id": log.receiver_acc_id, "status": log.status,
            "timestamp": log.timestamp.isoformat()}


# --- служебные ---------------------------------------------------------------
@bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "finance-system"})


# --- аутентификация ----------------------------------------------------------
@bp.post("/login")
def login():
    data = _json_body()
    ok, message, user = AuthService.authenticate(data.get("username", ""), data.get("password", ""))
    if not ok:
        return jsonify({"error": message, "status": 401}), 401
    return jsonify({"token": issue_token(user), "user": _user_view(user)}), 200


@bp.get("/me")
@api_auth()
def me():
    return jsonify({"user": _user_view(g.api_user)})


# --- справочники ------------------------------------------------------------
@bp.get("/banks")
@api_auth()
def banks():
    return jsonify({"banks": [{"id": bank.id, "name": bank.name} for bank in BankRepository.get_all()]})


@bp.get("/enterprises")
@api_auth()
def enterprises():
    return jsonify({"enterprises": [
        {"id": enterprise.id, "name": enterprise.name}
        for enterprise in EnterpriseRepository.get_all()
    ]})


# --- клиент -----------------------------------------------------------------
@bp.get("/accounts")
@api_auth(ROLE_CLIENT)
def accounts():
    items = AccountRepository.get_user_accounts(g.api_user.id)
    return jsonify({"accounts": [_account_view(account) for account in items]})


@bp.post("/accounts")
@api_auth(ROLE_CLIENT)
def open_account():
    data = _json_body()
    try:
        bank_id = int(data.get("bank_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "bank_id должен быть числом", "status": 400}), 400
    acc_type = data.get("acc_type", ACC_CHECKING)
    if acc_type not in (ACC_CHECKING, ACC_SAVING):
        return jsonify({"error": "acc_type: checking или saving", "status": 400}), 400
    ok, message = BankService.open_account(g.api_user.id, bank_id, acc_type)
    if not ok:
        return jsonify({"error": message, "status": 400}), 400
    account = AccountRepository.get_user_accounts(g.api_user.id)[-1]
    return jsonify({"message": message, "account": _account_view(account)}), 201


@bp.get("/accounts/<int:account_id>")
@api_auth(ROLE_CLIENT)
def account_detail(account_id: int):
    account = AccountRepository.get_for_user(account_id, g.api_user.id)
    if account is None:
        return jsonify({"error": "счёт не найден", "status": 404}), 404
    return jsonify({"account": _account_view(account)})


@bp.post("/accounts/<int:account_id>/close")
@api_auth(ROLE_CLIENT)
def close_account(account_id: int):
    ok, message = BankService.close_account(g.api_user.id, account_id)
    if not ok:
        status = 404 if "не найден" in message else 400
        return jsonify({"error": message, "status": status}), status
    return jsonify({"message": message})


@bp.post("/accounts/accumulate")
@api_auth(ROLE_CLIENT)
def accumulate():
    ok, message = BankService.accumulate(g.api_user.id)
    if not ok:
        return jsonify({"error": message, "status": 400}), 400
    return jsonify({"message": message})


@bp.post("/transfer")
@api_auth(ROLE_CLIENT)
def transfer():
    data = _json_body()
    amount, error = _amount(data.get("amount"))
    if error:
        return jsonify({"error": error, "status": 400}), 400
    try:
        from_id = int(data.get("from_id"))
        to_id = int(data.get("to_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "from_id и to_id должны быть числами", "status": 400}), 400

    ok, message = BankService.transfer(g.api_user.id, from_id, to_id, amount)
    if not ok:
        status = 404 if "не найден" in message else 403 if "заблокирован" in message else 400
        return jsonify({"error": message, "status": status}), status
    return jsonify({"message": message})


@bp.get("/history")
@api_auth(ROLE_CLIENT)
def history():
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50
    logs = BankService.history(g.api_user.id)[:limit]
    return jsonify({"history": [_log_view(log) for log in logs]})


@bp.get("/salary/requests")
@api_auth(ROLE_CLIENT)
def salary_requests():
    items = SalaryRequestRepository.get_for_user(g.api_user.id)
    return jsonify({"requests": [
        {"id": item.id, "enterprise_id": item.enterprise_id,
         "enterprise": item.enterprise.name if item.enterprise else None,
         "status": item.status, "status_title": item.status_title,
         "last_paid_at": item.last_paid_at.isoformat() if item.last_paid_at else None}
        for item in items
    ]})


@bp.post("/salary/apply")
@api_auth(ROLE_CLIENT)
def salary_apply():
    data = _json_body()
    try:
        enterprise_id = int(data.get("enterprise_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "enterprise_id должен быть числом", "status": 400}), 400
    ok, message = BankService.apply_for_salary(g.api_user.id, enterprise_id)
    if not ok:
        return jsonify({"error": message, "status": 400}), 400
    return jsonify({"message": message}), 201


@bp.post("/salary/pay")
@api_auth(ROLE_CLIENT)
def salary_pay():
    data = _json_body()
    try:
        enterprise_id = int(data.get("enterprise_id"))
        account_id = int(data.get("account_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "enterprise_id и account_id должны быть числами",
                        "status": 400}), 400
    ok, message = BankService.pay_salary(g.api_user.id, enterprise_id, account_id)
    if not ok:
        status = 403 if "не являетесь" in message else 400
        return jsonify({"error": message, "status": status}), status
    return jsonify({"message": message})


# --- менеджер ---------------------------------------------------------------
@bp.get("/manager/clients")
@api_auth(ROLE_MANAGER)
def manager_clients():
    items = ManagerService.pending_clients()
    return jsonify({"clients": [_user_view(client) for client in items]})


@bp.post("/manager/clients/<int:user_id>/<string:decision>")
@api_auth(ROLE_MANAGER)
def manager_client_decision(user_id: int, decision: str):
    if decision == "approve":
        ok, message = ManagerService.approve_client(g.api_user.id, user_id)
    elif decision == "reject":
        ok, message = ManagerService.reject_client(g.api_user.id, user_id)
    else:
        return jsonify({"error": "decision: approve или reject", "status": 400}), 400
    if not ok:
        return jsonify({"error": message, "status": 400}), 400
    return jsonify({"message": message})


@bp.get("/manager/requests")
@api_auth(ROLE_MANAGER)
def manager_requests():
    items = ManagerService.all_requests()
    return jsonify({"requests": [
        {"id": item.id, "user_id": item.user_id,
         "user": item.user.username if item.user else None,
         "enterprise_id": item.enterprise_id,
         "enterprise": item.enterprise.name if item.enterprise else None,
         "status": item.status}
        for item in items
    ]})


@bp.post("/manager/requests/<int:request_id>/<string:decision>")
@api_auth(ROLE_MANAGER)
def manager_request_decision(request_id: int, decision: str):
    data = request.get_json(silent=True) or {}
    if decision == "approve":
        amount = data.get("salary_amount", 1000.0)
        error = check_amount_value(float(amount)) if isinstance(amount, (int, float)) else "сумма"
        if error:
            return jsonify({"error": error, "status": 400}), 400
        ok, message = ManagerService.approve_request(g.api_user.id, request_id, float(amount))
    elif decision == "reject":
        ok, message = ManagerService.reject_request(g.api_user.id, request_id)
    elif decision == "revoke":
        ok, message = ManagerService.revoke_request(g.api_user.id, request_id)
    else:
        return jsonify({"error": "decision: approve, reject или revoke", "status": 400}), 400
    if not ok:
        return jsonify({"error": message, "status": 400}), 400
    return jsonify({"message": message})


@bp.get("/manager/accounts")
@api_auth(ROLE_MANAGER)
def manager_accounts():
    return jsonify({"accounts": [_account_view(account) for account in ManagerService.accounts()]})


@bp.post("/manager/accounts/<int:account_id>/<string:action>")
@api_auth(ROLE_MANAGER)
def manager_account_action(account_id: int, action: str):
    if action not in ("block", "unblock"):
        return jsonify({"error": "action: block или unblock", "status": 400}), 400
    ok, message = ManagerService.set_blocked(g.api_user.id, account_id, action == "block")
    if not ok:
        return jsonify({"error": message, "status": 400}), 400
    return jsonify({"message": message})


@bp.get("/manager/history")
@api_auth(ROLE_MANAGER)
def manager_history():
    try:
        user_id = int(request.args.get("user_id", ""))
    except ValueError:
        return jsonify({"error": "user_id обязателен", "status": 400}), 400
    logs = ManagerService.user_history(user_id)
    return jsonify({"history": [_log_view(log) for log in logs]})


# --- администратор ----------------------------------------------------------
@bp.get("/admin/logs")
@api_auth(ROLE_ADMIN)
def admin_logs():
    try:
        limit = int(request.args.get("limit", "200"))
    except ValueError:
        limit = 200
    logs = AdminService.logs(limit)
    return jsonify({"logs": [_log_view(log) for log in logs]})


@bp.post("/admin/logs/<int:log_id>/undo")
@api_auth(ROLE_ADMIN)
def admin_undo(log_id: int):
    ok, message = AdminService.undo(log_id, g.api_user.id)
    if not ok:
        status = 404 if "не найдена" in message else 400
        return jsonify({"error": message, "status": status}), status
    return jsonify({"message": message})

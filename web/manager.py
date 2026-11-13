"""Страницы менеджера: регистрации, заявки, счета, предприятия и штат."""
from flask import Blueprint, g, redirect, render_template, request, url_for

from repositories.user_repository import UserRepository
from services.manager_service import ManagerService
from services.validators import format_money, parse_amount
from web.helpers import audit, flash_result, manager_required

bp = Blueprint("manager", __name__, url_prefix="/manager")


@bp.get("/clients")
@manager_required
def clients():
    return render_template("manager/clients.html", clients=ManagerService.pending_clients())


@bp.post("/clients/<int:user_id>/approve")
@manager_required
def approve_client(user_id: int):
    ok, message = ManagerService.approve_client(g.user.id, user_id)
    flash_result(ok, message)
    audit(f"подтверждение клиента {user_id}: {message}")
    return redirect(request.referrer or url_for("manager.clients"))


@bp.post("/clients/<int:user_id>/reject")
@manager_required
def reject_client(user_id: int):
    ok, message = ManagerService.reject_client(g.user.id, user_id)
    flash_result(ok, message)
    audit(f"отклонение клиента {user_id}: {message}")
    return redirect(request.referrer or url_for("manager.clients"))


@bp.get("/requests")
@manager_required
def requests_list():
    return render_template(
        "manager/requests.html",
        requests=ManagerService.all_requests(),
        money=format_money,
    )


@bp.post("/requests/<int:request_id>/approve")
@manager_required
def approve_request(request_id: int):
    amount, error = parse_amount(request.form.get("salary_amount"))
    if error and request.form.get("salary_amount"):
        flash_result(False, error)
        return redirect(url_for("manager.requests_list"))
    ok, message = ManagerService.approve_request(g.user.id, request_id, amount or 1000.0)
    flash_result(ok, message)
    audit(f"подтверждение заявки {request_id}: {message}")
    return redirect(url_for("manager.requests_list"))


@bp.post("/requests/<int:request_id>/reject")
@manager_required
def reject_request(request_id: int):
    ok, message = ManagerService.reject_request(g.user.id, request_id)
    flash_result(ok, message)
    audit(f"отклонение заявки {request_id}: {message}")
    return redirect(url_for("manager.requests_list"))


@bp.post("/requests/<int:request_id>/revoke")
@manager_required
def revoke_request(request_id: int):
    ok, message = ManagerService.revoke_request(g.user.id, request_id)
    flash_result(ok, message)
    audit(f"отзыв заявки {request_id}: {message}")
    return redirect(url_for("manager.requests_list"))


@bp.get("/accounts")
@manager_required
def accounts():
    return render_template(
        "manager/accounts.html",
        accounts=ManagerService.accounts(),
        money=format_money,
    )


@bp.post("/accounts/<int:account_id>/block")
@manager_required
def block_account(account_id: int):
    ok, message = ManagerService.set_blocked(g.user.id, account_id, True)
    flash_result(ok, message)
    audit(f"блокировка счёта {account_id}: {message}")
    return redirect(request.referrer or url_for("manager.accounts"))


@bp.post("/accounts/<int:account_id>/unblock")
@manager_required
def unblock_account(account_id: int):
    ok, message = ManagerService.set_blocked(g.user.id, account_id, False)
    flash_result(ok, message)
    audit(f"разблокировка счёта {account_id}: {message}")
    return redirect(request.referrer or url_for("manager.accounts"))


@bp.get("/enterprises")
@manager_required
def enterprises():
    data = [
        (enterprise, ManagerService.staff(enterprise.id))
        for enterprise in ManagerService.enterprises()
    ]
    return render_template("manager/enterprises.html", data=data, money=format_money)


@bp.post("/enterprises/<int:enterprise_id>/fire/<int:user_id>")
@manager_required
def fire_employee(enterprise_id: int, user_id: int):
    ok, message = ManagerService.fire_employee(g.user.id, user_id, enterprise_id)
    flash_result(ok, message)
    audit(f"увольнение {user_id} из {enterprise_id}: {message}")
    return redirect(url_for("manager.enterprises"))


@bp.get("/history")
@manager_required
def history():
    user_id = _query_int("user_id")
    client = UserRepository.get_by_id(user_id) if user_id else None
    logs = ManagerService.user_history(user_id) if client else []
    return render_template(
        "manager/history.html", client=client, logs=logs, money=format_money, user_id=user_id,
    )


def _query_int(name: str) -> int | None:
    raw = (request.args.get(name) or "").strip()
    try:
        return int(raw)
    except ValueError:
        return None

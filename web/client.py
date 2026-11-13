"""Страницы клиента: счета и вклады, переводы, зарплата, история."""
from flask import Blueprint, g, redirect, render_template, request, url_for

from models import ACCOUNT_TYPES
from repositories.account_repository import AccountRepository
from repositories.bank_repository import BankRepository
from repositories.employment_repository import EmploymentRepository
from repositories.enterprise_repository import EnterpriseRepository
from repositories.salary_repository import SalaryRequestRepository
from services.bank_service import BankService
from services.validators import format_money, parse_amount
from web.helpers import audit, client_required, flash_result, form_int, form_value

bp = Blueprint("client", __name__)


def _active_accounts(user_id: int) -> list:
    """Счета, с которых можно платить: открытые и не заблокированные."""
    return [
        account
        for account in AccountRepository.get_user_accounts(user_id)
        if not account.is_blocked
    ]


@bp.get("/accounts")
@client_required
def accounts():
    return render_template(
        "client/accounts.html",
        accounts=AccountRepository.get_user_accounts(g.user.id, include_closed=True),
        banks=BankRepository.get_all(),
        account_types=ACCOUNT_TYPES,
        money=format_money,
    )


@bp.post("/accounts/open")
@client_required
def open_account():
    ok, message = BankService.open_account(
        g.user.id, form_int("bank_id") or 0, form_value("acc_type"),
    )
    flash_result(ok, message)
    audit(f"открытие счёта: {message}")
    return redirect(url_for("client.accounts"))


@bp.post("/accounts/<int:account_id>/close")
@client_required
def close_account(account_id: int):
    ok, message = BankService.close_account(g.user.id, account_id)
    flash_result(ok, message)
    audit(f"закрытие счёта {account_id}: {message}")
    return redirect(url_for("client.accounts"))


@bp.post("/accounts/accumulate")
@client_required
def accumulate():
    ok, message = BankService.accumulate(g.user.id)
    flash_result(ok, message)
    audit(f"начисление процентов: {message}")
    return redirect(url_for("client.accounts"))


@bp.route("/transfer", methods=["GET", "POST"])
@client_required
def transfer():
    accounts_list = _active_accounts(g.user.id)
    if request.method == "POST":
        amount, error = parse_amount(request.form.get("amount"))
        if error:
            flash_result(False, error)
        else:
            ok, message = BankService.transfer(
                g.user.id,
                form_int("from_id") or 0,
                form_int("to_id") or 0,
                amount,
            )
            flash_result(ok, message)
            audit(f"перевод: {message}")
            if ok:
                return redirect(url_for("client.transfer"))
    return render_template(
        "client/transfer.html",
        accounts=accounts_list,
        money=format_money,
        balance=sum(account.balance for account in accounts_list),
    )


@bp.get("/salary")
@client_required
def salary():
    requests = SalaryRequestRepository.get_for_user(g.user.id)
    employments = EmploymentRepository.get_for_user(g.user.id)
    enterprises = {employment.enterprise_id: employment for employment in employments}
    return render_template(
        "client/salary.html",
        enterprises=EnterpriseRepository.get_all(),
        requests=requests,
        employments=employments,
        enterprise_map=enterprises,
        accounts=_active_accounts(g.user.id),
        money=format_money,
    )


@bp.post("/salary/apply")
@client_required
def salary_apply():
    ok, message = BankService.apply_for_salary(g.user.id, form_int("enterprise_id") or 0)
    flash_result(ok, message)
    audit(f"заявка на зарплатный проект: {message}")
    return redirect(url_for("client.salary"))


@bp.post("/salary/pay")
@client_required
def salary_pay():
    ok, message = BankService.pay_salary(
        g.user.id,
        form_int("enterprise_id") or 0,
        form_int("account_id") or 0,
    )
    flash_result(ok, message)
    audit(f"выплата зарплаты: {message}")
    return redirect(url_for("client.salary"))


@bp.get("/history")
@client_required
def history():
    return render_template(
        "client/history.html",
        logs=BankService.history(g.user.id),
        money=format_money,
    )

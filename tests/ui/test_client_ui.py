"""Браузерные тесты страниц клиента и адаптивности."""
import pytest

from extensions import db
from models import ACC_CHECKING, ACC_SAVING, Account
from tests.factories import create_account, create_bank, create_user, login as _login
from tests.ui.pages.client_pages import AccountsPage, HistoryPage, TransferPage
from tests.ui.pages.login_page import LoginPage

pytestmark = pytest.mark.ui


def prepare_client(app, balance: float = 1000.0):
    with app.app_context():
        user = create_user("client1")
        bank = create_bank("МТБанк")
        first = create_account(user, bank, ACC_CHECKING, balance)
        second = create_account(user, bank, ACC_SAVING, 0.0)
        return {"first": first.id, "second": second.id, "bank": bank.name}


def test_client_opens_account(app, page, live_server):
    with app.app_context():
        create_user("client1")
        create_bank("МТБанк")
    LoginPage(page, live_server).open().login("client1", "secret123")

    accounts = AccountsPage(page, live_server).open()
    assert "МТБанк" in accounts.banks_in_form

    accounts.open_account("МТБанк", ACC_SAVING)

    accounts.wait_flash("открыт")
    assert any("МТБанк" in row for row in accounts.rows)


def test_client_transfers_and_sees_history(app, page, live_server):
    ids = prepare_client(app, 1000.0)
    LoginPage(page, live_server).open().login("client1", "secret123")

    transfer = TransferPage(page, live_server).open()
    transfer.select_accounts(str(ids["first"]), str(ids["second"])).submit("250")

    transfer.wait_flash("выполнен")
    with app.app_context():
        assert db.session.get(Account, ids["first"]).balance == 750.0
        assert db.session.get(Account, ids["second"]).balance == 250.0

    history = HistoryPage(page, live_server).open()
    assert any("перевод" in row and "250" in row for row in history.rows)


def test_client_transfer_validation_message(app, page, live_server):
    ids = prepare_client(app, 10.0)
    LoginPage(page, live_server).open().login("client1", "secret123")

    transfer = TransferPage(page, live_server).open()
    transfer.select_accounts(str(ids["first"]), str(ids["second"])).submit("999999")

    transfer.wait_flash("недостаточно средств")


def test_client_cannot_open_manager_pages(app, page, live_server):
    with app.app_context():
        create_user("client1")
    LoginPage(page, live_server).open().login("client1", "secret123")

    response = page.goto(f"{live_server}/manager/accounts")
    page.wait_for_load_state("networkidle")

    assert response.status == 403
    assert page.locator("h1").inner_text() in {"Нет доступа", "403 — нет доступа"}


def test_mobile_accounts_page_has_no_horizontal_scroll(app, mobile_page, live_server):
    with app.app_context():
        user = create_user("client1")
        bank = create_bank("МТБанк")
        create_account(user, bank, ACC_CHECKING, 1000.0)

    LoginPage(mobile_page, live_server).open().login("client1", "secret123")
    mobile_page.goto(f"{live_server}/accounts")
    mobile_page.wait_for_load_state("networkidle")

    metrics = mobile_page.evaluate(
        "() => ({scroll: document.documentElement.scrollWidth, "
        "client: document.documentElement.clientWidth})"
    )
    assert metrics["scroll"] <= metrics["client"]

    first_row = mobile_page.locator("table.table tbody tr").first
    assert first_row.is_visible()
    assert mobile_page.locator("td[data-label='Баланс']").first.is_visible()


def test_logo_links_home_and_favicon_available(app, page, live_server):
    with app.app_context():
        create_user("client1")
    LoginPage(page, live_server).open().login("client1", "secret123")

    logo = page.locator("a.logo")
    assert logo.get_attribute("href") == "/"

    icon = page.locator("link[rel=icon]").get_attribute("href")
    response = page.request.get(f"{live_server}{icon}")
    assert response.status == 200
    assert "svg" in response.headers.get("content-type", "")

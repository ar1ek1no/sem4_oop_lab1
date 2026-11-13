"""Браузерные тесты страниц менеджера и администратора."""
import pytest

from extensions import db
from models import ACC_CHECKING, ACTION_TRANSFER, Account, TransactionLog
from tests.factories import create_account, create_bank, create_user
from tests.ui.pages.client_pages import AccountsPage
from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.manager_pages import AdminLogsPage, ManagerClientsPage

pytestmark = pytest.mark.ui


def login(page, live_server, username, password="secret123"):
    LoginPage(page, live_server).open().login(username, password)


def test_manager_approves_client(app, page, live_server):
    with app.app_context():
        create_user("manager1", role="manager")
        create_user("client3", approved=False)

    login(page, live_server, "manager1")
    clients = ManagerClientsPage(page, live_server).open()
    assert any("client3" in name for name in clients.usernames)

    clients.approve("client3")
    clients.wait_flash("подтверждён")

    page.goto(f"{live_server}/logout")
    login(page, live_server, "client3")
    assert AccountsPage(page, live_server).heading == "Счета и вклады"


def test_manager_rejects_client(app, page, live_server):
    with app.app_context():
        create_user("manager1", role="manager")
        create_user("client3", approved=False)

    login(page, live_server, "manager1")
    clients = ManagerClientsPage(page, live_server).open().reject("client3")

    clients.wait_flash("отклонена")

    page.goto(f"{live_server}/logout")
    LoginPage(page, live_server).open().login("client3", "secret123")
    assert "отклонена" in page.locator(".flash").inner_text()


def test_admin_undoes_transfer(app, page, live_server):
    with app.app_context():
        create_user("admin1", role="admin")
        user = create_user("client1")
        bank = create_bank("МТБанк")
        first = create_account(user, bank, ACC_CHECKING, 1000.0)
        second = create_account(user, bank, ACC_CHECKING, 0.0)
        ids = {"first": first.id, "second": second.id}

    login(page, live_server, "client1")
    page.goto(f"{live_server}/transfer")
    page.select_option("select[name=from_id]", value=str(ids["first"]))
    page.select_option("select[name=to_id]", value=str(ids["second"]))
    page.fill("input[name=amount]", "100")
    page.get_by_role("button", name="Перевести").click()
    page.wait_for_load_state("networkidle")

    page.goto(f"{live_server}/logout")
    login(page, live_server, "admin1")
    logs = AdminLogsPage(page, live_server).open()
    assert any("перевод" in row for row in logs.rows)

    logs.undo_first()
    logs.wait_flash("отменено")

    with app.app_context():
        assert db.session.get(Account, ids["first"]).balance == 1000.0
        assert db.session.get(Account, ids["second"]).balance == 0.0
        assert db.session.query(TransactionLog).filter_by(
            action_type=ACTION_TRANSFER).first().status == "cancelled"

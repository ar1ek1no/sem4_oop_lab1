"""Браузерные тесты: вход и регистрация (Page Object)."""
import pytest

from tests.factories import create_user
from tests.ui.pages.client_pages import AccountsPage
from tests.ui.pages.login_page import LoginPage, RegisterPage

pytestmark = pytest.mark.ui


def test_login_success(app, page, live_server):
    with app.app_context():
        create_user("client1")

    LoginPage(page, live_server).open().login("client1", "secret123")

    accounts = AccountsPage(page, live_server)
    assert accounts.heading == "Счета и вклады"
    assert page.locator(".badge-role").inner_text() == "клиент"
    assert "Иванова" not in accounts.heading


def test_login_failure_shows_error(app, page, live_server):
    with app.app_context():
        create_user("client1")

    login = LoginPage(page, live_server).open().login("client1", "wrong")

    assert "неверный логин или пароль" in login.error


def test_register_new_client(page, live_server):
    register = RegisterPage(page, live_server).open()
    register.register("newclient", "Новиков Пётр", "secret123")

    assert "менеджер" in page.locator(".flash").inner_text()
    assert page.url.endswith("/login")


def test_register_shows_field_errors(page, live_server):
    register = RegisterPage(page, live_server).open()
    register.register("ab", "", "1")

    errors = register.field_errors
    assert len(errors) == 3
    assert any("логин" in error for error in errors)


def test_logout_returns_to_login(app, page, live_server):
    with app.app_context():
        create_user("client1")
    LoginPage(page, live_server).open().login("client1", "secret123")

    page.click("button:has-text('Выйти')")
    page.wait_for_load_state("networkidle")

    assert page.url.endswith("/login")
    assert "Вход в систему" in page.locator("h1").inner_text()


def test_no_console_errors_on_main_pages(app, page, live_server, ui_console_errors):
    with app.app_context():
        create_user("client1")
    LoginPage(page, live_server).open().login("client1", "secret123")

    for path in ("/accounts", "/transfer", "/salary", "/history"):
        page.goto(f"{live_server}{path}")
        page.wait_for_load_state("networkidle")
        assert page.locator("h1").inner_text() != "Ошибка запроса"

    assert ui_console_errors == []
    assert AccountsPage(page, live_server).open().heading == "Счета и вклады"

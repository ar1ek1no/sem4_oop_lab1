"""Фикстуры браузерных тестов: живой сервер, браузер, скриншот при падении."""
import os
import threading

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from tests.ui.pages.base_page import SCREENSHOTS


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(playwright_instance):
    """Браузер выбирается переменной окружения UI_BROWSER (chromium по умолчанию)."""
    name = os.environ.get("UI_BROWSER", "chromium")
    browser = getattr(playwright_instance, name).launch()
    yield browser
    browser.close()


@pytest.fixture
def live_server(app):
    """Поднимает приложение на свободном порту в отдельном потоке."""
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture
def page(browser, live_server, request):
    context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ru-RU")
    page = context.new_page()
    errors: list[str] = []
    request.node.console_errors = errors
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    # формы с data-confirm спрашивают подтверждение — в тестах соглашаемся
    page.on("dialog", lambda dialog: dialog.accept())
    yield page
    context.close()


@pytest.fixture
def mobile_page(browser, live_server, request):
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                                  locale="ru-RU")
    page = context.new_page()
    errors: list[str] = []
    request.node.console_errors = errors
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    # формы с data-confirm спрашивают подтверждение — в тестах соглашаемся
    page.on("dialog", lambda dialog: dialog.accept())
    yield page
    context.close()


@pytest.fixture
def ui_console_errors(request):
    return request.node.console_errors


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, "rep_" + report.when, report)
    if report.when == "call" and report.failed:
        page = item.funcargs.get("page") or item.funcargs.get("mobile_page")
        if page is not None:
            SCREENSHOTS.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(SCREENSHOTS / f"FAILED-{item.name}.png"), full_page=True)

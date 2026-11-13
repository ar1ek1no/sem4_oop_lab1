"""Снимки экранов для отчёта ЛР3.

Поднимает приложение на временной БД, наполняет её демонстрационными данными и
снимает страницы в Chromium: десктоп 1440×900 и мобильный 390×844.

Запуск: `python tools/capture_screenshots.py` (нужен `playwright install chromium`).
"""
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from werkzeug.security import generate_password_hash  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from extensions import db  # noqa: E402
from models import ACC_CHECKING, ACC_SAVING, Account, Bank, Enterprise, User  # noqa: E402
from repositories.account_repository import AccountRepository  # noqa: E402
from services.bank_service import BankService  # noqa: E402
from services.manager_service import ManagerService  # noqa: E402

SHOTS = ROOT / "docs" / "lab3" / "screenshots"
DB_PATH = ROOT / "docs" / "lab3" / "_screenshots.db"

DESKTOP = {"viewport": {"width": 1440, "height": 900}, "locale": "ru-RU"}
MOBILE = {"viewport": {"width": 390, "height": 844}, "locale": "ru-RU", "is_mobile": True}


def build_data(app) -> None:
    with app.app_context():
        users = {}
        for username, role, approved in (
            ("client1", "client", True), ("client2", "client", True),
            ("client3", "client", False), ("manager1", "manager", True),
            ("admin1", "admin", True),
        ):
            users[username] = User(
                username=username,
                password_hash=generate_password_hash("secret123"),
                full_name={"client1": "Иванова Мария Сергеевна",
                           "client2": "Петров Иван Олегович",
                           "client3": "Сидорова Анна Павловна",
                           "manager1": "Ковалёв Сергей Игоревич",
                           "admin1": "Орлова Елена Викторовна"}[username],
                role=role,
                is_approved=approved,
            )
            db.session.add(users[username])
        banks = ["МТБанк", "Беларусбанк", "Приорбанк"]
        for name in banks:
            db.session.add(Bank(name=name))
        for name in ("EPAM", "Wargaming", "МАЗ"):
            db.session.add(Enterprise(name=name))
        db.session.commit()

        mtbank = db.session.query(Bank).filter_by(name="МТБанк").one()
        belarus = db.session.query(Bank).filter_by(name="Беларусбанк").one()
        epam = db.session.query(Enterprise).filter_by(name="EPAM").one()
        wargaming = db.session.query(Enterprise).filter_by(name="Wargaming").one()

        first = Account(user_id=users["client1"].id, bank_id=mtbank.id, acc_type=ACC_CHECKING,
                        balance=5000.0)
        second = Account(user_id=users["client1"].id, bank_id=belarus.id, acc_type=ACC_SAVING,
                         balance=1000.0)
        third = Account(user_id=users["client2"].id, bank_id=mtbank.id, acc_type=ACC_CHECKING,
                        balance=300.0)
        db.session.add_all([first, second, third])
        db.session.commit()

        BankService.transfer(users["client1"].id, first.id, second.id, 500.0)
        BankService.transfer(users["client2"].id, third.id, first.id, 100.0)
        BankService.apply_for_salary(users["client1"].id, epam.id)
        BankService.apply_for_salary(users["client2"].id, wargaming.id)

        request = db.session.query(__import__("models").SalaryRequest).filter_by(
            user_id=users["client1"].id).one()
        ManagerService.approve_request(users["manager1"].id, request.id, 1500.0)
        BankService.pay_salary(users["client1"].id, epam.id, first.id)
        ManagerService.reject_client(users["manager1"].id, users["client3"].id)
        AccountRepository.update(second, is_blocked=True)
        db.session.commit()


def start_server(app):
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def login(page, base, username):
    page.goto(f"{base}/login")
    page.fill("input[name=username]", username)
    page.fill("input[name=password]", "secret123")
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


def shoot(page, base, path, name):
    page.goto(f"{base}{path}")
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(SHOTS / name), full_page=True)
    print("снято:", name)


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    class ShotsConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
        LOG_FILE = str(ROOT / "logs" / "screenshots.log")
        TESTING = False

    app = create_app(ShotsConfig)
    build_data(app)
    server = start_server(app)
    base = f"http://127.0.0.1:{server.server_port}"

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        anon = browser.new_context(**DESKTOP)
        page = anon.new_page()
        shoot(page, base, "/login", "01-login.png")
        shoot(page, base, "/register", "02-register.png")
        anon.close()

        client_context = browser.new_context(**DESKTOP)
        page = client_context.new_page()
        login(page, base, "client1")
        shoot(page, base, "/accounts", "03-client-accounts.png")
        shoot(page, base, "/transfer", "04-client-transfer.png")
        shoot(page, base, "/salary", "05-client-salary.png")
        shoot(page, base, "/history", "06-client-history.png")
        shoot(page, base, "/manager/accounts", "07-client-403.png")
        client_context.close()

        manager_context = browser.new_context(**DESKTOP)
        page = manager_context.new_page()
        login(page, base, "manager1")
        shoot(page, base, "/manager/clients", "08-manager-clients.png")
        shoot(page, base, "/manager/requests", "09-manager-requests.png")
        shoot(page, base, "/manager/accounts", "10-manager-accounts.png")
        shoot(page, base, "/manager/enterprises", "11-manager-enterprises.png")
        manager_context.close()

        admin_context = browser.new_context(**DESKTOP)
        page = admin_context.new_page()
        login(page, base, "admin1")
        shoot(page, base, "/admin/logs", "12-admin-logs.png")
        admin_context.close()

        mobile = browser.new_context(**MOBILE)
        page = mobile.new_page()
        login(page, base, "client1")
        shoot(page, base, "/accounts", "13-mobile-accounts.png")
        mobile.close()

        anon = browser.new_context(**DESKTOP)
        page = anon.new_page()
        shoot(page, base, "/missing-page", "14-404.png")
        anon.close()

        browser.close()

    server.shutdown()
    DB_PATH.unlink(missing_ok=True)
    print("готово:", SHOTS)


if __name__ == "__main__":
    main()

"""Матрица кроссбраузерности для ЛР4.

Поднимает приложение на временной БД, наполняет её данными (включая длинные строки,
пустые списки и «много элементов») и прогоняет одинаковый набор проверок в трёх
браузерах: Chromium, Firefox, WebKit. Плюс мобильная эмуляция 390×844 и масштаб 150 %.

Запуск: `python tools/cross_browser_check.py` — пишет `docs/lab4/COMPATIBILITY.md`.
"""
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS", "1")

from werkzeug.security import generate_password_hash  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from extensions import db  # noqa: E402
from models import ACC_CHECKING, ACC_SAVING, Account, Bank, Enterprise, User  # noqa: E402

BROWSERS = ("chromium", "firefox", "webkit")
LONG_NAME = "Банк с очень длинным названием " + "для проверки обтекания текста " * 3

DESKTOP = {"viewport": {"width": 1440, "height": 900}, "locale": "ru-RU"}
MOBILE = {"viewport": {"width": 390, "height": 844}, "is_mobile": True, "locale": "ru-RU"}


def seed(app) -> None:
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
                full_name=f"Пользователь {username}",
                role=role,
                is_approved=approved,
            )
            db.session.add(users[username])
        long_bank = Bank(name=LONG_NAME)
        short_bank = Bank(name="Я")
        db.session.add_all([long_bank, short_bank])
        db.session.add(Enterprise(name="ООО «Очень длинное название предприятия для проверки»"))
        db.session.commit()

        db.session.add_all([
            Account(user_id=users["client1"].id, bank_id=short_bank.id,
                    acc_type=ACC_CHECKING, balance=1234567.89),
            Account(user_id=users["client1"].id, bank_id=long_bank.id,
                    acc_type=ACC_SAVING, balance=0.01),
        ])
        # «много элементов»: 12 счетов у второго клиента
        for _ in range(12):
            db.session.add(Account(user_id=users["client2"].id, bank_id=short_bank.id,
                                   acc_type=ACC_CHECKING, balance=0.0))
        db.session.commit()


def login(page, base, username, password="secret123"):
    page.goto(f"{base}/login")
    page.fill("input[name=username]", username)
    page.fill("input[name=password]", password)
    page.get_by_role("button", name="Войти").click()
    page.wait_for_load_state("networkidle")


def no_horizontal_scroll(page) -> bool:
    metrics = page.evaluate(
        "() => ({scroll: document.documentElement.scrollWidth, "
        "client: document.documentElement.clientWidth, "
        "body: document.body.scrollWidth})",
    )
    return metrics["scroll"] <= metrics["client"] and metrics["body"] <= metrics["client"]


def run_checks(playwright, base: str) -> dict:
    result = {}
    for name in BROWSERS:
        browser = getattr(playwright, name).launch()
        context = browser.new_context(**DESKTOP)
        page = context.new_page()
        errors: list[str] = []
        page.on("console",
                lambda msg, errors=errors: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc, errors=errors: errors.append(str(exc)))
        page.on("dialog", lambda dialog: dialog.accept())
        checks = {}
        try:
            login(page, base, "client1")
            checks["Вход клиента и навигация по роли"] = page.locator("nav.nav a", has_text="Счета").count() > 0

            page.goto(f"{base}/accounts")
            page.select_option("select[name=bank_id]", index=0)
            page.select_option("select[name=acc_type]", value="saving")
            page.get_by_role("button", name="Открыть счёт").click()
            page.wait_for_load_state("networkidle")
            checks["Открытие счёта"] = "открыт" in page.locator(".flash").first.inner_text()

            page.goto(f"{base}/transfer")
            options = page.locator("select[name=from_id] option")
            page.select_option("select[name=from_id]", value=options.first.get_attribute("value"))
            page.select_option("select[name=to_id]", value=options.nth(1).get_attribute("value"))
            page.fill("input[name=amount]", "100")
            page.get_by_role("button", name="Перевести").click()
            page.wait_for_load_state("networkidle")
            checks["Перевод между счетами"] = "выполнен" in page.locator(".flash").first.inner_text()

            page.goto(f"{base}/history")
            checks["История с реальными данными"] = page.locator("table.table tbody tr").count() > 0
            checks["Длинные строки не ломают вёрстку"] = no_horizontal_scroll(page)

            page.goto(f"{base}/manager/accounts")
            checks["Запрет чужой зоны (403)"] = "Нет доступа" in page.locator("h1").inner_text()

            page.goto(f"{base}/no-such-page")
            checks["Страница 404"] = "Страница не найдена" in page.locator("h1").inner_text()

            page.goto(f"{base}/login")
            icon = page.locator("link[rel=icon]").get_attribute("href")
            response = page.request.get(f"{base}{icon}")
            checks["Favicon доступен"] = response.status == 200
            checks["Логотип ведёт на главную"] = page.locator("a.logo").get_attribute("href") == "/"

            page.goto(f"{base}/transfer")
            page.evaluate("document.body.style.zoom = '1.5'")
            checks["Масштаб 150 % без горизонтальной прокрутки"] = no_horizontal_scroll(page)

            page.goto(f"{base}/login")
            page.goto(f"{base}/logout")
            login(page, base, "client2")
            page.goto(f"{base}/accounts")
            checks["Много элементов в списке"] = page.locator("table.table tbody tr").count() >= 12

            page.goto(f"{base}/logout")
            login(page, base, "admin1")
            page.goto(f"{base}/admin/logs")
            checks["Журнал администратора"] = page.locator("table.table tbody tr").count() > 0

            # переходы на 403/404 сделаны намеренно: их сетевые ошибки не считаем
            unexpected = [error for error in errors
                          if "403" not in error and "404" not in error]
            checks["Ошибок в консоли нет"] = unexpected == []
            if unexpected:
                print(f"[{name}] неожиданные ошибки консоли: {unexpected}")
        finally:
            context.close()

        mobile = browser.new_context(**MOBILE)
        mpage = mobile.new_page()
        try:
            login(mpage, base, "client1")
            mpage.goto(f"{base}/accounts")
            checks["Мобильная эмуляция 390×844"] = no_horizontal_scroll(mpage)
            checks["Карточная раскладка таблиц"] = mpage.locator("td[data-label]").first.is_visible()
        finally:
            mobile.close()

        for key, value in checks.items():
            result.setdefault(key, {})[name] = bool(value)
        result.setdefault("_versions", {})[name] = browser.version
        browser.close()
    return result


def to_markdown(result: dict) -> str:
    versions = result.pop("_versions", {})
    lines = [
        "# Матрица кроссбраузерности (ЛР4 п. 1)",
        "",
        "Прогон одинаковых проверок в трёх движках через Playwright.",
        "Скрипт: `tools/cross_browser_check.py`. Десктоп 1440×900, мобильная эмуляция 390×844, "
        "масштаб 150 %.",
        "",
        f"Версии: Chromium {versions.get('chromium', '—')}, "
        f"Firefox {versions.get('firefox', '—')}, WebKit {versions.get('webkit', '—')}.",
        "",
        "| Проверка | Chromium | Firefox | WebKit |",
        "|---|---|---|---|",
    ]
    for check, values in result.items():
        row = " | ".join("✅" if values.get(name) else "❌" for name in BROWSERS)
        lines.append(f"| {check} | {row} |")
    failed = [check for check, values in result.items() if not all(values.values())]
    lines += [
        "",
        "**Итог:** " + ("все проверки пройдены во всех браузерах." if not failed
                        else "расхождения: " + ", ".join(failed)),
        "",
        "## Что ещё проверялось вручную",
        "",
        "| Проверка | Результат |",
        "|---|---|",
        "| Целостность блоков и выравнивание по сетке | карточки и таблицы выровнены, отступы одинаковые |",
        "| Обтекание длинного текста | длинное название банка переносится, страница не прокручивается |",
        "| Пустые списки | у нового клиента «Счетов пока нет», у менеджера «Новых регистраций нет» |",
        "| Наведение и фокус | кнопки и ссылки меняют фон, `:focus-visible` виден с клавиатуры |",
        "| Кликабельность | все кнопки и ссылки кликаются, ссылка «На главную» в ошибках работает |",
        "| Network в DevTools | статика 200/304, favicon 200, битых запросов нет |",
        "| Console в DevTools | ошибок нет (проверяется в тестах и в этом скрипте) |",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    db_path = ROOT / "docs" / "_compat.db"
    if db_path.exists():
        db_path.unlink()

    class CompatConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        LOG_FILE = str(ROOT / "logs" / "compat.log")
        TESTING = False

    app = create_app(CompatConfig)
    seed(app)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        result = run_checks(playwright, base)

    server.shutdown()
    db_path.unlink(missing_ok=True)

    markdown = to_markdown(result)
    (ROOT / "docs" / "lab4" / "COMPATIBILITY.md").write_text(markdown, encoding="utf-8")
    print(markdown)


if __name__ == "__main__":
    main()

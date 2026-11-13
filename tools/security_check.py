"""Проверки безопасности для ЛР4 п. 3.

Поднимает приложение на временной БД и проверяет: доступ к закрытым зонам без входа,
подмену идентификатора (IDOR), отсутствие технических деталей в ошибках, логирование.
Результат — `docs/api-security/SECURITY.md` с фактическими ответами сервера.

Запуск: `python tools/security_check.py`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from extensions import db  # noqa: E402
from models import ACC_CHECKING, Account, Bank, Enterprise, User  # noqa: E402

DB_PATH = ROOT / "docs" / "api-security" / "_security.db"
LOG_PATH = ROOT / "docs" / "api-security" / "_security.log"


def seed(app):
    with app.app_context():
        users = {}
        for username, role in (("client1", "client"), ("client2", "client"),
                               ("manager1", "manager"), ("admin1", "admin")):
            users[username] = User(
                username=username,
                password_hash=generate_password_hash("secret123"),
                full_name=f"Пользователь {username}",
                role=role,
                is_approved=True,
            )
            db.session.add(users[username])
        bank = Bank(name="МТБанк")
        db.session.add(bank)
        db.session.add(Enterprise(name="EPAM"))
        db.session.commit()
        first = Account(user_id=users["client1"].id, bank_id=bank.id, acc_type=ACC_CHECKING,
                        balance=1000.0)
        foreign = Account(user_id=users["client2"].id, bank_id=bank.id, acc_type=ACC_CHECKING,
                          balance=500.0)
        db.session.add_all([first, foreign])
        db.session.commit()
        return {"own": first.id, "foreign": foreign.id}


def api_client(client, username):
    token = client.post("/api/v1/login",
                        json={"username": username, "password": "secret123"}).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    for path in (DB_PATH, LOG_PATH):
        path.unlink(missing_ok=True)

    class SecurityConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
        LOG_FILE = str(LOG_PATH)
        TESTING = False
        PROPAGATE_EXCEPTIONS = False

    app = create_app(SecurityConfig)
    ids = seed(app)
    client = app.test_client()
    rows = []

    def check(title, response, expected_status, marker=None, forbidden=()):
        body = response.get_data(as_text=True)
        ok = response.status_code == expected_status
        if marker is not None:
            ok = ok and marker in body
        leaks = [word for word in forbidden if word in body]
        rows.append({
            "title": title,
            "request": getattr(response, "request", None),
            "status": response.status_code,
            "ok": ok and not leaks,
            "leaks": leaks,
        })
        return body

    # 1. прямой доступ без входа
    for path in ("/accounts", "/transfer", "/manager/accounts", "/admin/logs"):
        response = client.get(path)
        check(f"Прямой URL {path} без входа", response, 302, forbidden=("Traceback",))
        rows[-1]["request"] = f"GET {path}"
        rows[-1]["expected"] = "302 на /login?next=..."

    # 2. API без токена
    response = client.get("/api/v1/accounts")
    check("API без токена", response, 401, marker="нужен заголовок")
    rows[-1]["request"] = "GET /api/v1/accounts"
    rows[-1]["expected"] = "401 JSON"

    # 3. IDOR: чужой счёт
    headers = api_client(client, "client1")
    response = client.get(f"/api/v1/accounts/{ids['foreign']}", headers=headers)
    check("Чужой счёт по id (IDOR)", response, 404, marker="не найден")
    rows[-1]["request"] = f"GET /api/v1/accounts/{ids['foreign']} (токен client1)"
    rows[-1]["expected"] = "404, данные не раскрыты"

    response = client.post(f"/api/v1/accounts/{ids['foreign']}/close", headers=headers)
    check("Закрытие чужого счёта", response, 404, marker="не найден")
    rows[-1]["request"] = f"POST /api/v1/accounts/{ids['foreign']}/close"
    rows[-1]["expected"] = "404, счёт не закрыт"

    response = client.post("/api/v1/transfer",
                           json={"from_id": ids["foreign"], "to_id": ids["own"], "amount": "10"},
                           headers=headers)
    check("Перевод с чужого счёта", response, 404, marker="не найден")
    rows[-1]["request"] = "POST /api/v1/transfer (from_id чужого счёта)"
    rows[-1]["expected"] = "404, баланс не изменён"

    # 4. чужая роль
    response = client.get("/api/v1/manager/clients", headers=headers)
    check("Клиент на ручке менеджера", response, 403, marker="недостаточно прав")
    rows[-1]["request"] = "GET /api/v1/manager/clients (токен client1)"
    rows[-1]["expected"] = "403"

    # 5. ошибки без технических деталей
    response = client.get("/api/v1/no-such-endpoint", headers=headers)
    check("Несуществующая ручка API", response, 404, forbidden=("Traceback", "sqlite", "/mnt/"))
    rows[-1]["request"] = "GET /api/v1/no-such-endpoint"
    rows[-1]["expected"] = "404 JSON без путей и SQL"

    response = client.get("/no-such-page")
    check("Несуществующая страница", response, 404, forbidden=("Traceback", "/mnt/", "sqlite"))
    rows[-1]["request"] = "GET /no-such-page"
    rows[-1]["expected"] = "404 без стека"

    # 6. ошибка 500 не раскрывает детали
    from unittest.mock import patch

    client.post("/login", data={"username": "client1", "password": "secret123"})
    with patch("repositories.account_repository.AccountRepository.get_user_accounts",
               side_effect=RuntimeError("SELECT * FROM users; /mnt/c/secret")):
        response = client.get("/accounts")
    check("Ошибка 500", response, 500, forbidden=("Traceback", "SELECT * FROM", "/mnt/"))
    rows[-1]["request"] = "GET /accounts при исключении в БД"
    rows[-1]["expected"] = "500 без SQL, путей и стека"

    # 7. логирование: неудачный вход проверяем в отдельной сессии,
    # иначе авторизованный пользователь просто получает редирект на главную
    anonymous = app.test_client()
    anonymous.post("/login", data={"username": "client1", "password": "wrong"})
    client.get("/logout")
    client.post("/login", data={"username": "client1", "password": "secret123"})
    log_text = LOG_PATH.read_text(encoding="utf-8")
    rows.append({
        "title": "Логирование входа и отказов",
        "request": "POST /login (успех и отказ)",
        "status": "—",
        "ok": "вход выполнен: client1" in log_text and "неудачный вход" in log_text,
        "leaks": [],
        "expected": "записи в logs/app.log",
    })
    rows.append({
        "title": "Пароль не попадает в лог",
        "request": "POST /login",
        "status": "—",
        "ok": "secret123" not in log_text,
        "leaks": [],
        "expected": "пароля в журнале нет",
    })

    lines = [
        "# Проверки безопасности (ЛР4 п. 3)",
        "",
        "Проверки выполнены скриптом `tools/security_check.py` на временной копии базы; "
        "он же формирует эту таблицу. Автоматические тесты, закрепляющие те же проверки: "
        "`tests/integration/test_api.py`, `tests/integration/test_errors.py`, "
        "`tests/integration/test_logging.py`, `tests/integration/test_client_web.py`.",
        "",
        "## 1. Доступ в закрытую зону без авторизации",
        "",
        "Анонимный запрос к любой странице каталога возвращает 302 на `/login?next=…`; "
        "сессия не создаётся, данные не отдаются. API отвечает 401 JSON.",
        "",
        "## 2. Подмена идентификатора (IDOR)",
        "",
        "Все операции с счётом идут через `AccountRepository.get_for_user(account_id, user_id)`. "
        "Чужой счёт для сервиса неотличим от несуществующего: ответ 404, данные не раскрываются, "
        "операция не выполняется. Тот же принцип в API и в формах страниц.",
        "",
        "## 3. Сообщения об ошибках",
        "",
        "Обработчики 400/401/403/404/405/500 отдают только текст для пользователя. "
        "Стек, пути файловой системы и SQL в ответ не попадают — проверяется поиском подстрок "
        "`Traceback`, `/mnt/`, `SELECT * FROM` в теле ответа.",
        "",
        "## 4. Логирование",
        "",
        "Каждое значимое действие пишется дважды: в журнал БД (`transaction_logs`, отмена опирается "
        "на `payload`) и в файл `logs/app.log` (входы, отказы, операции). Пароли и содержимое сессии "
        "в файл не попадают.",
        "",
        "## Результаты",
        "",
        "| Проверка | Запрос | Ожидание | Факт | Результат |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        status = row["status"]
        result = "✅" if row["ok"] else "❌"
        fact = f"{status}" if status != "—" else "запись есть" if row["ok"] else "нет записи"
        if row["leaks"]:
            fact += f", утечка: {', '.join(row['leaks'])}"
        lines.append(f"| {row['title']} | `{row['request']}` | {row['expected']} | {fact} | {result} |")

    failed = [row["title"] for row in rows if not row["ok"]]
    lines += [
        "",
        f"**Итог:** {'все проверки пройдены' if not failed else 'проблемы: ' + ', '.join(failed)}.",
        "",
    ]
    (ROOT / "docs" / "api-security" / "SECURITY.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    for path in (DB_PATH, LOG_PATH):
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

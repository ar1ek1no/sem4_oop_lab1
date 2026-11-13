"""Сборка Postman-коллекции и окружения для API (ЛР4 п. 2).

Запуск: `python tools/build_postman_collection.py` — создаёт
`docs/lab4/postman/FinanceSystem.postman_collection.json` и `...local.postman_environment.json`.

Коллекция покрывает все варианты использования: вход по токену, справочники, счета,
переводы, зарплату, роли менеджера и администратора, негативные проверки.
Связывание запросов — через переменные коллекции (токен из логина подставляется дальше).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTMAN = ROOT / "docs" / "lab4" / "postman"
BASE_URL = "http://127.0.0.1:5005"


def assertion_lines(name: str, code: int, extra: str = "") -> list[str]:
    body = [f"pm.test('{name}', () => pm.response.to.have.status({code}));"]
    if extra:
        body.append(extra)
    return body


def request_item(name: str, method: str, path: str, *, body=None, tests=None,
                 save=None, auth=True, token="{{clientToken}}"):
    headers = [{"key": "Content-Type", "value": "application/json"}] if body else []
    if auth:
        headers.append({"key": "Authorization", "value": f"Bearer {token}"})
    item = {
        "name": name,
        "request": {
            "method": method,
            "header": headers,
            "url": {
                "raw": "{{baseUrl}}" + path,
                "host": ["{{baseUrl}}"],
                "path": [part for part in path.strip("/").split("/") if part],
            },
        },
        "event": [{"listen": "test", "script": {"type": "text/javascript",
                                                "exec": (tests or []) + (save or [])}}],
    }
    if body is not None:
        item["request"]["body"] = {"mode": "raw", "raw": json.dumps(body, ensure_ascii=False)}
    return item


def save_var(name: str, expression: str) -> list[str]:
    return [f"pm.collectionVariables.set('{name}', {expression});"]


def build() -> dict:
    folders = []

    auth = [
        request_item(
            "Вход клиента (успех)", "POST", "/api/v1/login",
            body={"username": "client1", "password": "client1"},
            auth=False,
            tests=assertion_lines("200 OK", 200,
                       "pm.test('есть токен', () => pm.expect(pm.response.json().token).to.be.a('string'));"),
            save=save_var("clientToken", "pm.response.json().token"),
        ),
        request_item(
            "Вход: неверный пароль", "POST", "/api/v1/login",
            body={"username": "client1", "password": "wrong"},
            auth=False,
            tests=assertion_lines("401 Unauthorized", 401,
                       "pm.test('сообщение об ошибке', () => pm.expect(pm.response.json().error).to.include('неверный'));"),
        ),
        request_item(
            "Текущий пользователь", "GET", "/api/v1/me",
            tests=assertion_lines("200 OK", 200,
                       "pm.test('роль клиент', () => pm.expect(pm.response.json().user.role).to.eql('client'));"),
            save=save_var("clientUserId", "pm.response.json().user.id"),
        ),
    ]
    folders.append({"name": "01 Аутентификация", "item": auth})

    dictionaries = [
        request_item(
            "Список банков", "GET", "/api/v1/banks",
            tests=assertion_lines("200 OK", 200,
                       "pm.test('банки есть', () => pm.expect(pm.response.json().banks.length).to.be.above(0));"),
            save=save_var("bankId", "pm.response.json().banks[0].id"),
        ),
        request_item(
            "Список предприятий", "GET", "/api/v1/enterprises",
            tests=assertion_lines("200 OK", 200,
                       "pm.test('предприятия есть', () => pm.expect(pm.response.json().enterprises.length).to.be.above(0));"),
            save=save_var("enterpriseId", "pm.response.json().enterprises[0].id"),
        ),
    ]
    folders.append({"name": "02 Справочники", "item": dictionaries})

    accounts = [
        request_item(
            "Мои счета", "GET", "/api/v1/accounts",
            tests=assertion_lines("200 OK", 200,
                       "pm.test('два счёта', () => pm.expect(pm.response.json().accounts.length).to.be.above(1));"),
            save=[
                "pm.collectionVariables.set('firstAccountId', pm.response.json().accounts[0].id);",
                "pm.collectionVariables.set('secondAccountId', pm.response.json().accounts[1].id);",
            ],
        ),
        request_item(
            "Открыть вклад", "POST", "/api/v1/accounts",
            body={"bank_id": "{{bankId}}", "acc_type": "saving"},
            tests=assertion_lines("201 Created", 201,
                       "pm.test('тип saving', () => pm.expect(pm.response.json().account.type).to.eql('saving'));"),
            save=save_var("newAccountId", "pm.response.json().account.id"),
        ),
        request_item(
            "Счёт по id (свой)", "GET", "/api/v1/accounts/{{firstAccountId}}",
            tests=assertion_lines("200 OK", 200,
                       "pm.test('совпал id', () => pm.expect(pm.response.json().account.id).to.eql(Number(pm.collectionVariables.get('firstAccountId'))));"),
        ),
        request_item(
            "Счёт по несуществующему id", "GET", "/api/v1/accounts/999999",
            tests=assertion_lines("404 Not Found", 404,
                       "pm.test('не раскрывает детали', () => pm.expect(pm.response.json().error).to.include('не найден'));"),
        ),
        request_item(
            "Открыть счёт: неизвестный банк", "POST", "/api/v1/accounts",
            body={"bank_id": 999999, "acc_type": "checking"},
            tests=assertion_lines("400 Bad Request", 400),
        ),
        request_item(
            "Открыть счёт: неверный тип", "POST", "/api/v1/accounts",
            body={"bank_id": "{{bankId}}", "acc_type": "deposit"},
            tests=assertion_lines("400 Bad Request", 400),
        ),
    ]
    folders.append({"name": "03 Счета", "item": accounts})

    transfers = [
        request_item(
            "Перевод между счетами", "POST", "/api/v1/transfer",
            body={"from_id": "{{firstAccountId}}", "to_id": "{{secondAccountId}}",
                  "amount": "150.50"},
            tests=assertion_lines("200 OK", 200,
                       "pm.test('перевод выполнен', () => pm.expect(pm.response.json().message).to.include('выполнен'));"),
        ),
        request_item(
            "Перевод: недостаточно средств", "POST", "/api/v1/transfer",
            body={"from_id": "{{firstAccountId}}", "to_id": "{{secondAccountId}}",
                  "amount": "99999"},
            tests=assertion_lines("400 Bad Request", 400,
                       "pm.test('недостаточно средств', () => pm.expect(pm.response.json().error).to.include('недостаточно'));"),
        ),
        request_item(
            "Перевод: нечисловая сумма", "POST", "/api/v1/transfer",
            body={"from_id": "{{firstAccountId}}", "to_id": "{{secondAccountId}}",
                  "amount": "abc"},
            tests=assertion_lines("400 Bad Request", 400),
        ),
        request_item(
            "Перевод: на тот же счёт", "POST", "/api/v1/transfer",
            body={"from_id": "{{firstAccountId}}", "to_id": "{{firstAccountId}}",
                  "amount": "10"},
            tests=assertion_lines("400 Bad Request", 400),
        ),
        request_item(
            "История операций", "GET", "/api/v1/history?limit=20",
            tests=assertion_lines("200 OK", 200,
                       "pm.test('есть перевод', () => pm.expect(pm.response.json().history.some(h => h.action === 'transfer')).to.be.true);"),
            save=save_var("transferLogId",
                          "pm.response.json().history.find(h => h.action === 'transfer').id"),
        ),
    ]
    folders.append({"name": "04 Переводы и история", "item": transfers})

    salary = [
        request_item(
            "Мои заявки", "GET", "/api/v1/salary/requests",
            tests=assertion_lines("200 OK", 200),
        ),
        request_item(
            "Подать заявку на зарплатный проект", "POST", "/api/v1/salary/apply",
            body={"enterprise_id": "{{enterpriseId}}"},
            tests=assertion_lines("201 Created", 201),
        ),
        request_item(
            "Повторная заявка отклонена", "POST", "/api/v1/salary/apply",
            body={"enterprise_id": "{{enterpriseId}}"},
            tests=assertion_lines("400 Bad Request", 400,
                       "pm.test('уже подана', () => pm.expect(pm.response.json().error).to.include('уже подана'));"),
        ),
        request_item(
            "Выплата без подтверждения", "POST", "/api/v1/salary/pay",
            body={"enterprise_id": "{{enterpriseId}}", "account_id": "{{firstAccountId}}"},
            tests=assertion_lines("403 Forbidden", 403,
                       "pm.test('вы не сотрудник', () => pm.expect(pm.response.json().error).to.include('не являетесь сотрудником'));"),
        ),
    ]
    folders.append({"name": "05 Зарплата (клиент)", "item": salary})

    manager = [
        request_item(
            "Вход менеджера", "POST", "/api/v1/login",
            body={"username": "manager1", "password": "manager1"},
            auth=False,
            tests=assertion_lines("200 OK", 200),
            save=save_var("managerToken", "pm.response.json().token"),
        ),
        request_item(
            "Заявки на подтверждение", "GET", "/api/v1/manager/clients", token="{{managerToken}}",
            tests=assertion_lines("200 OK", 200,
                       "pm.test('есть ожидающие', () => pm.expect(pm.response.json().clients.length).to.be.above(0));"),
            save=save_var("pendingClientId", "pm.response.json().clients[0].id"),
        ),
        request_item(
            "Подтвердить клиента", "POST", "/api/v1/manager/clients/{{pendingClientId}}/approve",
            token="{{managerToken}}",
            tests=assertion_lines("200 OK", 200),
        ),
        request_item(
            "Заявки на зарплатный проект", "GET", "/api/v1/manager/requests", token="{{managerToken}}",
            tests=assertion_lines("200 OK", 200,
                       "pm.test('есть заявка', () => pm.expect(pm.response.json().requests.length).to.be.above(0));"),
            save=save_var("pendingRequestId",
                          "pm.response.json().requests.find(r => r.status === 'pending').id"),
        ),
        request_item(
            "Подтвердить заявку с окладом", "POST",
            "/api/v1/manager/requests/{{pendingRequestId}}/approve",
            token="{{managerToken}}",
            body={"salary_amount": 1500},
            tests=assertion_lines("200 OK", 200),
        ),
        request_item(
            "Счета клиентов", "GET", "/api/v1/manager/accounts", token="{{managerToken}}",
            tests=assertion_lines("200 OK", 200),
        ),
        request_item(
            "Заблокировать счёт", "POST", "/api/v1/manager/accounts/{{secondAccountId}}/block",
            token="{{managerToken}}",
            tests=assertion_lines("200 OK", 200),
        ),
        request_item(
            "Разблокировать счёт", "POST", "/api/v1/manager/accounts/{{secondAccountId}}/unblock",
            token="{{managerToken}}",
            tests=assertion_lines("200 OK", 200),
        ),
        request_item(
            "История клиента", "GET", "/api/v1/manager/history?user_id={{clientUserId}}",
            token="{{managerToken}}",
            tests=assertion_lines("200 OK", 200),
        ),
    ]
    folders.append({"name": "06 Менеджер", "item": manager})

    admin = [
        request_item(
            "Вход администратора", "POST", "/api/v1/login",
            body={"username": "admin1", "password": "admin1"},
            auth=False,
            tests=assertion_lines("200 OK", 200),
            save=save_var("adminToken", "pm.response.json().token"),
        ),
        request_item(
            "Журнал действий", "GET", "/api/v1/admin/logs?limit=50", token="{{adminToken}}",
            tests=assertion_lines("200 OK", 200,
                       "pm.test('журнал не пуст', () => pm.expect(pm.response.json().logs.length).to.be.above(0));"),
        ),
        request_item(
            "Отменить перевод", "POST", "/api/v1/admin/logs/{{transferLogId}}/undo",
            token="{{adminToken}}",
            tests=assertion_lines("200 OK", 200,
                       "pm.test('отменено', () => pm.expect(pm.response.json().message).to.include('отменено'));"),
        ),
        request_item(
            "Повторная отмена невозможна", "POST", "/api/v1/admin/logs/{{transferLogId}}/undo",
            token="{{adminToken}}",
            tests=assertion_lines("400 Bad Request", 400,
                       "pm.test('уже отменено', () => pm.expect(pm.response.json().error).to.include('уже отменено'));"),
        ),
    ]
    folders.append({"name": "07 Администратор", "item": admin})

    negative = [
        request_item("Без токена", "GET", "/api/v1/accounts", auth=False,
                     tests=assertion_lines("401 Unauthorized", 401)),
        request_item("Неверный токен", "GET", "/api/v1/accounts",
                     token="broken.token.value",
                     tests=assertion_lines("401 Unauthorized", 401)),
        request_item("Несуществующая ручка", "GET", "/api/v1/no-such-endpoint",
                     tests=assertion_lines("404 Not Found", 404,
                                "pm.test('JSON-ошибка', () => pm.expect(pm.response.json().status).to.eql(404));")),
        request_item("Чужая роль", "GET", "/api/v1/manager/clients",
                     tests=assertion_lines("403 Forbidden", 403)),
    ]
    folders.append({"name": "08 Негативные проверки", "item": negative})

    return {
        "info": {
            "_postman_id": "6f0d9a3e-2c7b-4f5e-9b1a-c5f8f0d2a111",
            "name": "Finance System API",
            "description": "Коллекция на все эндпоинты вариантов использования. "
                           "Перед запуском: python seed.py, затем flask --app app run --port 5005.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": folders,
        "variable": [
            {"key": "baseUrl", "value": BASE_URL},
            {"key": "clientToken", "value": ""},
            {"key": "managerToken", "value": ""},
            {"key": "adminToken", "value": ""},
            {"key": "clientUserId", "value": ""},
            {"key": "bankId", "value": ""},
            {"key": "enterpriseId", "value": ""},
            {"key": "firstAccountId", "value": ""},
            {"key": "secondAccountId", "value": ""},
            {"key": "newAccountId", "value": ""},
            {"key": "pendingClientId", "value": ""},
            {"key": "pendingRequestId", "value": ""},
            {"key": "transferLogId", "value": ""},
        ],
    }


def environment() -> dict:
    return {
        "id": "b3f1c2d4-1111-4aaa-8bbb-9ccc00001111",
        "name": "Finance System — local",
        # токены НЕ задаются в окружении: иначе пустое значение окружения
        # перекрывает переменную коллекции, установленную тестом логина
        "values": [
            {"key": "baseUrl", "value": BASE_URL, "enabled": True},
        ],
        "_postman_variable_scope": "environment",
    }


def main() -> None:
    POSTMAN.mkdir(parents=True, exist_ok=True)
    (POSTMAN / "FinanceSystem.postman_collection.json").write_text(
        json.dumps(build(), ensure_ascii=False, indent=2), encoding="utf-8",
    )
    (POSTMAN / "local.postman_environment.json").write_text(
        json.dumps(environment(), ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print("коллекция и окружение собраны в", POSTMAN)


if __name__ == "__main__":
    main()

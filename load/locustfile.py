"""Профиль нагрузки для Locust (ЛР5).

Сценарий повторяет типичную сессию клиента: вход, просмотр счетов и истории,
справочник банков и изредка небольшой перевод. Именно перевод — запись в SQLite,
поэтому он и создаёт конкуренцию за базу.

Запуск:
    locust -f load/locustfile.py --host http://127.0.0.1:5005
    locust -f load/locustfile.py --headless -u 20 -r 5 -t 30s --host http://127.0.0.1:5005
"""
import random

from locust import HttpUser, between, task


class ClientUser(HttpUser):
    """Клиент: чтение счетов и истории, редкие переводы."""

    wait_time = between(1, 3)
    weight = 4

    def on_start(self):
        response = self.client.post(
            "/api/v1/login",
            json={"username": "client1", "password": "client1"},
            name="/api/v1/login",
        )
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        accounts = self.client.get("/api/v1/accounts", headers=self.headers,
                                   name="/api/v1/accounts").json()["accounts"]
        self.account_ids = [account["id"] for account in accounts]

    @task(6)
    def list_accounts(self):
        self.client.get("/api/v1/accounts", headers=self.headers, name="/api/v1/accounts")

    @task(4)
    def history(self):
        self.client.get("/api/v1/history?limit=20", headers=self.headers,
                        name="/api/v1/history")

    @task(2)
    def banks(self):
        self.client.get("/api/v1/banks", headers=self.headers, name="/api/v1/banks")

    @task(1)
    def transfer(self):
        if len(self.account_ids) < 2:
            return
        first, second = self.account_ids[0], self.account_ids[1]
        self.client.post(
            "/api/v1/transfer",
            json={"from_id": first, "to_id": second, "amount": "0.01"},
            headers=self.headers,
            name="/api/v1/transfer",
        )


class ManagerUser(HttpUser):
    """Менеджер: смотрит регистрации, заявки и счета — только чтение."""

    wait_time = between(2, 4)
    weight = 1

    def on_start(self):
        response = self.client.post(
            "/api/v1/login",
            json={"username": "manager1", "password": "manager1"},
            name="/api/v1/login",
        )
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def pending_clients(self):
        self.client.get("/api/v1/manager/clients", headers=self.headers,
                        name="/api/v1/manager/clients")

    @task(2)
    def requests(self):
        self.client.get("/api/v1/manager/requests", headers=self.headers,
                        name="/api/v1/manager/requests")

    @task(2)
    def accounts(self):
        self.client.get("/api/v1/manager/accounts", headers=self.headers,
                        name="/api/v1/manager/accounts")

    @task(1)
    def random_history(self):
        self.client.get(f"/api/v1/manager/history?user_id={random.randint(1, 3)}",
                        headers=self.headers, name="/api/v1/manager/history")

"""Фабрики тестовых данных: тест создаёт только то, что ему нужно."""
from werkzeug.security import generate_password_hash

from extensions import db
from models import (
    ACC_CHECKING,
    ACCOUNT_TYPES,
    REQ_PENDING,
    ROLE_CLIENT,
    Account,
    Bank,
    Employment,
    Enterprise,
    SalaryRequest,
    User,
)


def create_user(username: str, password: str = "secret123", role: str = ROLE_CLIENT,
                approved: bool = True, full_name: str | None = None) -> User:
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        full_name=full_name or f"Тестовый {username}",
        role=role,
        is_approved=approved,
    )
    db.session.add(user)
    db.session.commit()
    return user


def create_bank(name: str = "Тест-Банк") -> Bank:
    bank = Bank(name=name)
    db.session.add(bank)
    db.session.commit()
    return bank


def create_enterprise(name: str = "ООО «Тест»") -> Enterprise:
    enterprise = Enterprise(name=name)
    db.session.add(enterprise)
    db.session.commit()
    return enterprise


def create_account(user: User, bank: Bank, acc_type: str = ACC_CHECKING,
                   balance: float = 0.0) -> Account:
    assert acc_type in ACCOUNT_TYPES
    account = Account(user_id=user.id, bank_id=bank.id, acc_type=acc_type, balance=balance)
    db.session.add(account)
    db.session.commit()
    return account


def create_employment(user: User, enterprise: Enterprise, salary: float = 1000.0) -> Employment:
    employment = Employment(user_id=user.id, enterprise_id=enterprise.id, salary_amount=salary)
    db.session.add(employment)
    db.session.commit()
    return employment


def create_request(user: User, enterprise: Enterprise, status: str = REQ_PENDING) -> SalaryRequest:
    request = SalaryRequest(user_id=user.id, enterprise_id=enterprise.id, status=status)
    db.session.add(request)
    db.session.commit()
    return request


def login(client, username: str, password: str = "secret123"):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=False)


def api_headers(client, username: str, password: str = "secret123") -> dict:
    response = client.post("/api/v1/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.get_json()
    token = response.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}

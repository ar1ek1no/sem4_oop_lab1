"""Сценарный тест: жизненный цикл заявки на зарплатный проект.

Цепочка вызовов приводит сущность из «нет заявки» в «выплата проведена» и обратно.
Соответствует диаграмме состояний (docs/STATE_DIAGRAM.md, сущность 1).
"""
from extensions import db
from models import (
    ACC_CHECKING,
    ACTION_SALARY,
    REQ_APPROVED,
    REQ_PENDING,
    Account,
    Employment,
    SalaryRequest,
    TransactionLog,
    User,
)
from tests.factories import create_account, create_bank, create_enterprise, create_user, login


def prepare(app):
    with app.app_context():
        create_user("client1")
        create_user("manager1", role="manager")
        create_user("admin1", role="admin")
        client = db.session.query(User).filter_by(username="client1").first()
        bank = create_bank("МТБанк")
        account = create_account(client, bank, ACC_CHECKING, 0.0)
        enterprise = create_enterprise("EPAM")
        return {"account": account.id, "enterprise": enterprise.id, "client": client.id}


def status_of(request_id):
    return db.session.get(SalaryRequest, request_id).status


def test_salary_lifecycle(app, client):
    ids = prepare(app)

    # 1. клиент подаёт заявку
    login(client, "client1")
    response = client.post("/salary/apply", data={"enterprise_id": ids["enterprise"]},
                           follow_redirects=True)
    assert "отправлена" in response.get_data(as_text=True)

    with app.app_context():
        request = db.session.query(SalaryRequest).one()
        request_id = request.id
        assert request.status == REQ_PENDING

    # 2. выплата до подтверждения невозможна
    response = client.post("/salary/pay", data={"enterprise_id": ids["enterprise"],
                                                "account_id": ids["account"]},
                           follow_redirects=True)
    assert "не являетесь сотрудником" in response.get_data(as_text=True)

    # 3. менеджер подтверждает с окладом
    client.post("/logout")
    login(client, "manager1")
    response = client.post(f"/manager/requests/{request_id}/approve",
                           data={"salary_amount": "1200"}, follow_redirects=True)
    assert "подтверждена" in response.get_data(as_text=True)

    with app.app_context():
        assert status_of(request_id) == REQ_APPROVED
        employment = db.session.query(Employment).one()
        assert employment.salary_amount == 1200.0

    # 4. клиент получает зарплату
    client.post("/logout")
    login(client, "client1")
    response = client.post("/salary/pay", data={"enterprise_id": ids["enterprise"],
                                                "account_id": ids["account"]},
                           follow_redirects=True)
    assert "зачислена" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Account, ids["account"]).balance == 1200.0
        assert db.session.get(SalaryRequest, request_id).last_paid_at is not None

    # 5. повторная выплата в том же периоде запрещена
    response = client.post("/salary/pay", data={"enterprise_id": ids["enterprise"],
                                                "account_id": ids["account"]},
                           follow_redirects=True)
    assert "уже выплачена" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Account, ids["account"]).balance == 1200.0

    # 6. администратор отменяет выплату
    client.post("/logout")
    login(client, "admin1")
    with app.app_context():
        log_id = db.session.query(TransactionLog).filter_by(action_type=ACTION_SALARY).one().id
    response = client.post(f"/admin/logs/{log_id}/undo", follow_redirects=True)
    assert "отменено" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Account, ids["account"]).balance == 0.0
        assert db.session.get(SalaryRequest, request_id).last_paid_at is None

    # 7. после отмены выплату можно провести снова
    client.post("/logout")
    login(client, "client1")
    response = client.post("/salary/pay", data={"enterprise_id": ids["enterprise"],
                                                "account_id": ids["account"]},
                           follow_redirects=True)
    assert "зачислена" in response.get_data(as_text=True)

    # 8. менеджер отзывает подтверждение — сотрудник уходит из штата
    client.post("/logout")
    login(client, "manager1")
    response = client.post(f"/manager/requests/{request_id}/revoke", follow_redirects=True)
    assert "отозвано" in response.get_data(as_text=True)
    with app.app_context():
        assert status_of(request_id) == REQ_PENDING
        assert db.session.query(Employment).count() == 0

    # 9. после отзыва выплата недоступна
    client.post("/logout")
    login(client, "client1")
    response = client.post("/salary/pay", data={"enterprise_id": ids["enterprise"],
                                                "account_id": ids["account"]},
                           follow_redirects=True)
    assert "не являетесь сотрудником" in response.get_data(as_text=True)


def test_rejected_request_cannot_be_paid(app, client):
    ids = prepare(app)
    login(client, "client1")
    client.post("/salary/apply", data={"enterprise_id": ids["enterprise"]})

    with app.app_context():
        request_id = db.session.query(SalaryRequest).one().id

    client.post("/logout")
    login(client, "manager1")
    client.post(f"/manager/requests/{request_id}/reject")

    client.post("/logout")
    login(client, "client1")
    response = client.post("/salary/pay", data={"enterprise_id": ids["enterprise"],
                                                "account_id": ids["account"]},
                           follow_redirects=True)
    assert "не являетесь сотрудником" in response.get_data(as_text=True)


def test_client_can_reapply_after_rejection(app, client):
    ids = prepare(app)
    login(client, "client1")
    client.post("/salary/apply", data={"enterprise_id": ids["enterprise"]})

    with app.app_context():
        request_id = db.session.query(SalaryRequest).one().id

    client.post("/logout")
    login(client, "manager1")
    client.post(f"/manager/requests/{request_id}/reject")
    client.post("/logout")

    login(client, "client1")
    response = client.post("/salary/apply", data={"enterprise_id": ids["enterprise"]},
                           follow_redirects=True)
    assert "отправлена" in response.get_data(as_text=True)
    with app.app_context():
        statuses = [request.status for request in db.session.query(SalaryRequest).all()]
        assert sorted(statuses) == sorted(["rejected", REQ_PENDING])

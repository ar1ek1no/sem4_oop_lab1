"""Интеграционные тесты страниц менеджера."""
from extensions import db
from models import (
    ACC_CHECKING,
    REQ_APPROVED,
    REQ_PENDING,
    REQ_REJECTED,
    Account,
    Employment,
    Enterprise,
    SalaryRequest,
    User,
)
from tests.factories import (
    create_account,
    create_bank,
    create_employment,
    create_enterprise,
    create_request,
    create_user,
    login,
)


def prepare(app):
    with app.app_context():
        manager = create_user("manager1", role="manager")
        client = create_user("client1", approved=False)
        approved_client = create_user("client2")
        bank = create_bank()
        account = create_account(approved_client, bank, ACC_CHECKING, 100.0)
        enterprise = create_enterprise("EPAM")
        request = create_request(approved_client, enterprise, REQ_PENDING)
        return {
            "manager": manager.id, "client": client.id,
            "approved_client": approved_client.id, "account": account.id,
            "enterprise": enterprise.id, "request": request.id, "bank": bank.id,
        }


def test_clients_page_lists_pending(app, client):
    prepare(app)
    login(client, "manager1")

    response = client.get("/manager/clients")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "client1" in text
    assert "client2" not in text.split("<tbody>")[1].split("</tbody>")[0]


def test_approve_client(app, client):
    ids = prepare(app)
    login(client, "manager1")

    response = client.post(f"/manager/clients/{ids['client']}/approve", follow_redirects=True)

    assert "подтверждён" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(User, ids["client"]).is_approved is True


def test_client_can_login_after_approval(app, client):
    ids = prepare(app)
    login(client, "manager1")
    client.post(f"/manager/clients/{ids['client']}/approve")
    client.post("/logout")

    response = client.post("/login", data={"username": "client1", "password": "secret123"},
                           follow_redirects=True)
    assert "Выйти" in response.get_data(as_text=True)


def test_reject_client_blocks_login(app, client):
    ids = prepare(app)
    login(client, "manager1")

    response = client.post(f"/manager/clients/{ids['client']}/reject", follow_redirects=True)
    assert "отклонена" in response.get_data(as_text=True)

    client.post("/logout")
    response = client.post("/login", data={"username": "client1", "password": "secret123"},
                           follow_redirects=True)
    assert "отклонена" in response.get_data(as_text=True)


def test_approve_unknown_client(app, client):
    prepare(app)
    login(client, "manager1")
    response = client.post("/manager/clients/9999/approve", follow_redirects=True)
    assert "клиент не найден" in response.get_data(as_text=True)


def test_requests_page(app, client):
    prepare(app)
    login(client, "manager1")

    response = client.get("/manager/requests")
    text = response.get_data(as_text=True)

    assert "client2" in text
    assert "EPAM" in text
    assert "ожидает решения" in text


def test_approve_request_with_salary(app, client):
    ids = prepare(app)
    login(client, "manager1")

    response = client.post(f"/manager/requests/{ids['request']}/approve",
                           data={"salary_amount": "1500"}, follow_redirects=True)

    assert "подтверждена" in response.get_data(as_text=True)
    with app.app_context():
        request = db.session.get(SalaryRequest, ids["request"])
        assert request.status == REQ_APPROVED
        employment = db.session.query(Employment).filter_by(
            user_id=ids["approved_client"], enterprise_id=ids["enterprise"]).first()
        assert employment.salary_amount == 1500.0


def test_approve_request_invalid_salary(app, client):
    ids = prepare(app)
    login(client, "manager1")
    client.post(f"/manager/requests/{ids['request']}/approve",
                data={"salary_amount": "abc"}, follow_redirects=True)
    with app.app_context():
        assert db.session.get(SalaryRequest, ids["request"]).status == REQ_PENDING


def test_reject_request(app, client):
    ids = prepare(app)
    login(client, "manager1")

    response = client.post(f"/manager/requests/{ids['request']}/reject", follow_redirects=True)

    assert "отклонена" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(SalaryRequest, ids["request"]).status == REQ_REJECTED


def test_revoke_request(app, client):
    ids = prepare(app)
    with app.app_context():
        request = db.session.get(SalaryRequest, ids["request"])
        request.status = REQ_APPROVED
        db.session.commit()
        create_employment(db.session.get(User, ids["approved_client"]),
                          db.session.get(Enterprise, ids["enterprise"]))
    login(client, "manager1")

    response = client.post(f"/manager/requests/{ids['request']}/revoke", follow_redirects=True)

    assert "отозвано" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(SalaryRequest, ids["request"]).status == REQ_PENDING


def test_accounts_page(app, client):
    ids = prepare(app)
    login(client, "manager1")

    response = client.get("/manager/accounts")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "client2" in text
    assert f"№{ids['account']}" not in text or str(ids["account"]) in text


def test_block_and_unblock_account(app, client):
    ids = prepare(app)
    login(client, "manager1")

    response = client.post(f"/manager/accounts/{ids['account']}/block", follow_redirects=True)
    assert "заблокирован" in response.get_data(as_text=True)

    with app.app_context():
        assert db.session.get(Account, ids["account"]).is_blocked is True

    response = client.post(f"/manager/accounts/{ids['account']}/unblock", follow_redirects=True)
    assert "разблокирован" in response.get_data(as_text=True)


def test_block_closed_account_denied(app, client):
    ids = prepare(app)
    with app.app_context():
        account = db.session.get(Account, ids["account"])
        account.is_closed = True
        db.session.commit()
    login(client, "manager1")

    response = client.post(f"/manager/accounts/{ids['account']}/block", follow_redirects=True)
    assert "счёт закрыт" in response.get_data(as_text=True)


def test_enterprises_page_and_fire(app, client):
    ids = prepare(app)
    with app.app_context():
        user = db.session.get(User, ids["approved_client"])
        enterprise = db.session.get(Enterprise, ids["enterprise"])
        create_employment(user, enterprise, 1200.0)
    login(client, "manager1")

    response = client.get("/manager/enterprises")
    text = response.get_data(as_text=True)
    assert "EPAM" in text
    assert "client2" in text

    response = client.post(
        f"/manager/enterprises/{ids['enterprise']}/fire/{ids['approved_client']}",
        follow_redirects=True,
    )
    assert "уволен" in response.get_data(as_text=True)


def test_user_history_page(app, client):
    ids = prepare(app)
    login(client, "manager1")

    response = client.get(f"/manager/history?user_id={ids['approved_client']}")
    assert response.status_code == 200
    assert "client2" in response.get_data(as_text=True)


def test_user_history_unknown_user(app, client):
    prepare(app)
    login(client, "manager1")

    response = client.get("/manager/history?user_id=9999")
    assert "не найден" in response.get_data(as_text=True)


def test_user_history_without_id(app, client):
    prepare(app)
    login(client, "manager1")

    response = client.get("/manager/history")
    assert response.status_code == 200


def test_manager_cannot_open_admin(app, client):
    prepare(app)
    login(client, "manager1")
    assert client.get("/admin/logs").status_code == 403

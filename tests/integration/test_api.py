"""Интеграционные тесты JSON API: коды ответов, структура, безопасность."""
from extensions import db
from models import ACC_CHECKING, ACC_SAVING, ACTION_TRANSFER, Account, TransactionLog, User
from tests.factories import (
    api_headers,
    create_account,
    create_bank,
    create_employment,
    create_enterprise,
    create_request,
    create_user,
)


def prepare(app):
    with app.app_context():
        client = create_user("client1")
        other = create_user("client2")
        create_user("manager1", role="manager")
        create_user("admin1", role="admin")
        bank = create_bank("МТБанк")
        checking = create_account(client, bank, ACC_CHECKING, 1000.0)
        saving = create_account(client, bank, ACC_SAVING, 0.0)
        foreign = create_account(other, bank, ACC_CHECKING, 100.0)
        enterprise = create_enterprise("EPAM")
        request = create_request(client, enterprise)
        create_employment(client, enterprise, 1200.0)
        return {
            "bank": bank.id, "checking": checking.id, "saving": saving.id,
            "foreign": foreign.id, "enterprise": enterprise.id, "request": request.id,
        }


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_login_returns_token(app, client):
    prepare(app)
    response = client.post("/api/v1/login", json={"username": "client1", "password": "secret123"})

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["token"]
    assert payload["user"]["role"] == "client"
    assert "password" not in payload["user"]


def test_login_bad_password(app, client):
    prepare(app)
    response = client.post("/api/v1/login", json={"username": "client1", "password": "bad"})
    assert response.status_code == 401
    assert "error" in response.get_json()


def test_login_without_json(client):
    response = client.post("/api/v1/login", data="not json")
    assert response.status_code == 400
    assert response.get_json()["status"] == 400


def test_me_and_unauthorized(app, client):
    prepare(app)
    headers = api_headers(client, "client1")
    response = client.get("/api/v1/me", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["user"]["username"] == "client1"

    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/me", headers={"Authorization": "Basic x"}).status_code == 401
    assert client.get("/api/v1/me",
                      headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_token_of_rejected_user(app, client):
    prepare(app)
    headers = api_headers(client, "client1")
    with app.app_context():
        user = db.session.query(User).filter_by(username="client1").first()
        user.is_rejected = True
        db.session.commit()
    assert client.get("/api/v1/me", headers=headers).status_code == 401


def test_dictionaries(app, client):
    prepare(app)
    headers = api_headers(client, "client1")
    banks = client.get("/api/v1/banks", headers=headers).get_json()["banks"]
    enterprises = client.get("/api/v1/enterprises", headers=headers).get_json()["enterprises"]
    assert banks and banks[0]["name"] == "МТБанк"
    assert enterprises and enterprises[0]["name"] == "EPAM"


def test_accounts_list_and_open(app, client):
    ids = prepare(app)
    headers = api_headers(client, "client1")

    response = client.get("/api/v1/accounts", headers=headers)
    assert response.status_code == 200
    assert len(response.get_json()["accounts"]) == 2

    response = client.post("/api/v1/accounts",
                           json={"bank_id": ids["bank"], "acc_type": ACC_SAVING},
                           headers=headers)
    assert response.status_code == 201
    assert response.get_json()["account"]["type"] == ACC_SAVING


def test_open_account_errors(app, client):
    prepare(app)
    headers = api_headers(client, "client1")

    assert client.post("/api/v1/accounts", json={"bank_id": "abc"},
                       headers=headers).status_code == 400
    assert client.post("/api/v1/accounts", json={"bank_id": 1, "acc_type": "deposit"},
                       headers=headers).status_code == 400
    assert client.post("/api/v1/accounts", json={"bank_id": 9999},
                       headers=headers).status_code == 400


def test_account_detail_idor(app, client):
    ids = prepare(app)
    headers = api_headers(client, "client1")

    own = client.get(f"/api/v1/accounts/{ids['checking']}", headers=headers)
    assert own.status_code == 200
    assert own.get_json()["account"]["id"] == ids["checking"]

    foreign = client.get(f"/api/v1/accounts/{ids['foreign']}", headers=headers)
    assert foreign.status_code == 404
    assert "не найден" in foreign.get_json()["error"]


def test_close_account(app, client):
    ids = prepare(app)
    headers = api_headers(client, "client1")

    assert client.post(f"/api/v1/accounts/{ids['checking']}/close",
                       headers=headers).status_code == 400
    assert client.post(f"/api/v1/accounts/{ids['saving']}/close",
                       headers=headers).status_code == 200
    assert client.post(f"/api/v1/accounts/{ids['foreign']}/close",
                       headers=headers).status_code == 404


def test_accumulate(app, client):
    prepare(app)
    headers = api_headers(client, "client1")
    assert client.post("/api/v1/accounts/accumulate", headers=headers).status_code == 400


def test_transfer_success_and_errors(app, client):
    ids = prepare(app)
    headers = api_headers(client, "client1")

    response = client.post("/api/v1/transfer",
                           json={"from_id": ids["checking"], "to_id": ids["saving"],
                                 "amount": "100.50"},
                           headers=headers)
    assert response.status_code == 200
    assert "выполнен" in response.get_json()["message"]

    with app.app_context():
        assert db.session.get(Account, ids["checking"]).balance == 899.5

    assert client.post("/api/v1/transfer",
                       json={"from_id": ids["checking"], "to_id": ids["saving"],
                             "amount": "abc"}, headers=headers).status_code == 400
    assert client.post("/api/v1/transfer",
                       json={"from_id": ids["foreign"], "to_id": ids["saving"],
                             "amount": "10"}, headers=headers).status_code == 404
    assert client.post("/api/v1/transfer",
                       json={"from_id": ids["checking"], "to_id": ids["checking"],
                             "amount": "10"}, headers=headers).status_code == 400


def test_history(app, client):
    ids = prepare(app)
    headers = api_headers(client, "client1")
    assert client.get("/api/v1/history?limit=abc", headers=headers).status_code == 200

    client.post("/api/v1/transfer",
                json={"from_id": ids["checking"], "to_id": ids["saving"], "amount": "1"},
                headers=headers)
    history = client.get("/api/v1/history", headers=headers).get_json()["history"]
    assert history and history[0]["action"] == ACTION_TRANSFER


def test_salary_endpoints(app, client):
    ids = prepare(app)
    headers = api_headers(client, "client1")

    requests = client.get("/api/v1/salary/requests", headers=headers).get_json()["requests"]
    assert len(requests) == 1

    assert client.post("/api/v1/salary/apply",
                       json={"enterprise_id": ids["enterprise"]},
                       headers=headers).status_code == 400
    assert client.post("/api/v1/salary/apply", json={"enterprise_id": "abc"},
                       headers=headers).status_code == 400

    # заявка в статусе pending — выплата невозможна
    assert client.post("/api/v1/salary/pay",
                       json={"enterprise_id": ids["enterprise"], "account_id": ids["saving"]},
                       headers=headers).status_code == 400


def test_manager_endpoints(app, client):
    ids = prepare(app)
    headers = api_headers(client, "manager1")

    clients = client.get("/api/v1/manager/clients", headers=headers)
    assert clients.status_code == 200

    requests = client.get("/api/v1/manager/requests", headers=headers).get_json()["requests"]
    assert any(item["id"] == ids["request"] for item in requests)

    assert client.post(f"/api/v1/manager/requests/{ids['request']}/approve",
                       json={"salary_amount": 1300}, headers=headers).status_code == 200
    assert client.post(f"/api/v1/manager/requests/{ids['request']}/approve",
                       json={"salary_amount": 1300}, headers=headers).status_code == 400
    assert client.post(f"/api/v1/manager/requests/{ids['request']}/unknown",
                       headers=headers).status_code == 400

    accounts = client.get("/api/v1/manager/accounts", headers=headers).get_json()["accounts"]
    assert accounts

    assert client.post(f"/api/v1/manager/accounts/{ids['checking']}/block",
                       headers=headers).status_code == 200
    assert client.post(f"/api/v1/manager/accounts/{ids['checking']}/unblock",
                       headers=headers).status_code == 200
    assert client.post(f"/api/v1/manager/accounts/{ids['checking']}/whatever",
                       headers=headers).status_code == 400
    assert client.post("/api/v1/manager/accounts/9999/block",
                       headers=headers).status_code == 400


def test_manager_clients_decisions(app, client):
    prepare(app)
    with app.app_context():
        pending = create_user("pending", approved=False)
        pending_id = pending.id
    headers = api_headers(client, "manager1")

    assert client.post(f"/api/v1/manager/clients/{pending_id}/approve",
                       headers=headers).status_code == 200
    assert client.post(f"/api/v1/manager/clients/{pending_id}/reject",
                       headers=headers).status_code == 200
    assert client.post(f"/api/v1/manager/clients/{pending_id}/unknown",
                       headers=headers).status_code == 400


def test_manager_history(app, client):
    ids = prepare(app)
    headers = api_headers(client, "manager1")
    assert client.get("/api/v1/manager/history", headers=headers).status_code == 400
    assert client.get(f"/api/v1/manager/history?user_id={ids['checking']}",
                      headers=headers).status_code == 200


def test_admin_endpoints(app, client):
    ids = prepare(app)
    client_headers = api_headers(client, "client1")
    client.post("/api/v1/transfer",
                json={"from_id": ids["checking"], "to_id": ids["saving"], "amount": "10"},
                headers=client_headers)

    with app.app_context():
        log_id = db.session.query(TransactionLog).filter_by(action_type=ACTION_TRANSFER).first().id

    headers = api_headers(client, "admin1")
    logs = client.get("/api/v1/admin/logs?limit=10", headers=headers).get_json()["logs"]
    assert logs

    assert client.post(f"/api/v1/admin/logs/{log_id}/undo", headers=headers).status_code == 200
    assert client.post(f"/api/v1/admin/logs/{log_id}/undo", headers=headers).status_code == 400
    assert client.post("/api/v1/admin/logs/9999/undo", headers=headers).status_code == 404


def test_role_separation(app, client):
    prepare(app)
    client_headers = api_headers(client, "client1")
    manager_headers = api_headers(client, "manager1")

    assert client.get("/api/v1/manager/clients", headers=client_headers).status_code == 403
    assert client.get("/api/v1/admin/logs", headers=client_headers).status_code == 403
    assert client.get("/api/v1/accounts", headers=manager_headers).status_code == 403


def test_unknown_api_endpoint_returns_json(client):
    response = client.get("/api/v1/unknown")
    assert response.status_code == 404
    assert response.is_json
    assert response.get_json()["status"] == 404

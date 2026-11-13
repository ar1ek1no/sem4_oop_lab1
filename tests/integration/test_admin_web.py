"""Интеграционные тесты страницы администратора: журнал и отмена."""
from extensions import db
from models import (
    ACC_CHECKING,
    ACTION_TRANSFER,
    ACTION_UNDO,
    LOG_CANCELLED,
    Account,
    TransactionLog,
)
from tests.factories import create_account, create_bank, create_user, login


def prepare(app):
    with app.app_context():
        create_user("admin1", role="admin")
        client = create_user("client1")
        bank = create_bank()
        first = create_account(client, bank, ACC_CHECKING, 1000.0)
        second = create_account(client, bank, ACC_CHECKING, 0.0)
        return {"first": first.id, "second": second.id}


def test_logs_page_requires_admin(app, client):
    prepare(app)
    login(client, "client1")
    assert client.get("/admin/logs").status_code == 403


def test_logs_page_lists_actions(app, client):
    ids = prepare(app)
    login(client, "client1")
    client.post("/transfer", data={"from_id": ids["first"], "to_id": ids["second"],
                                   "amount": "100"})
    client.post("/logout")

    login(client, "admin1")
    response = client.get("/admin/logs")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "перевод" in text
    assert "client1" in text


def test_logs_filter_by_action(app, client):
    ids = prepare(app)
    login(client, "client1")
    client.post("/accounts/open", data={"bank_id": 1, "acc_type": "checking"})
    client.post("/transfer", data={"from_id": ids["first"], "to_id": ids["second"],
                                   "amount": "10"})
    client.post("/logout")

    login(client, "admin1")
    response = client.get(f"/admin/logs?action={ACTION_TRANSFER}")

    text = response.get_data(as_text=True).split("<tbody>")[1]
    assert "перевод" in text
    assert "открытие счёта" not in text


def test_logs_limit_ignores_invalid_value(app, client):
    prepare(app)
    login(client, "admin1")
    assert client.get("/admin/logs?limit=abc").status_code == 200


def test_undo_transfer_restores_balances(app, client):
    ids = prepare(app)
    login(client, "client1")
    client.post("/transfer", data={"from_id": ids["first"], "to_id": ids["second"],
                                   "amount": "100"})
    client.post("/logout")

    with app.app_context():
        log = (db.session.query(TransactionLog)
               .filter_by(action_type=ACTION_TRANSFER).first())
        log_id = log.id

    login(client, "admin1")
    response = client.post(f"/admin/logs/{log_id}/undo", follow_redirects=True)

    assert "отменено" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Account, ids["first"]).balance == 1000.0
        assert db.session.get(Account, ids["second"]).balance == 0.0
        assert db.session.get(TransactionLog, log_id).status == LOG_CANCELLED
        assert db.session.query(TransactionLog).filter_by(action_type=ACTION_UNDO).count() == 1


def test_undo_twice(app, client):
    ids = prepare(app)
    login(client, "client1")
    client.post("/transfer", data={"from_id": ids["first"], "to_id": ids["second"],
                                   "amount": "100"})
    client.post("/logout")

    with app.app_context():
        log_id = db.session.query(TransactionLog).filter_by(action_type=ACTION_TRANSFER).first().id

    login(client, "admin1")
    client.post(f"/admin/logs/{log_id}/undo")
    response = client.post(f"/admin/logs/{log_id}/undo", follow_redirects=True)

    assert "уже отменено" in response.get_data(as_text=True)


def test_undo_legacy_log_without_payload(app, client):
    prepare(app)
    with app.app_context():
        legacy = TransactionLog(action_type=ACTION_TRANSFER, amount=10.0,
                                sender_acc_id=1, receiver_acc_id=2, payload=None)
        db.session.add(legacy)
        db.session.commit()
        legacy_id = legacy.id

    login(client, "admin1")
    response = client.post(f"/admin/logs/{legacy_id}/undo", follow_redirects=True)

    assert "старой версией" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(TransactionLog, legacy_id).status != LOG_CANCELLED


def test_undo_missing_log(app, client):
    prepare(app)
    login(client, "admin1")
    response = client.post("/admin/logs/9999/undo", follow_redirects=True)
    assert "не найдена" in response.get_data(as_text=True)

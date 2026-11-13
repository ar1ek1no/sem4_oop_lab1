"""Сценарный тест: жизненный цикл счёта (открыт → заблокирован → закрыт)."""
from extensions import db
from models import ACC_CHECKING, ACC_SAVING, Account, User
from tests.factories import create_account, create_bank, create_user, login


def prepare(app):
    with app.app_context():
        create_user("client1")
        create_user("manager1", role="manager")
        client = db.session.query(User).filter_by(username="client1").first()
        bank = create_bank("МТБанк")
        source = create_account(client, bank, ACC_CHECKING, 1000.0)
        target = create_account(client, bank, ACC_SAVING, 0.0)
        return {"source": source.id, "target": target.id, "bank": bank.id}


def balance(account_id):
    return db.session.get(Account, account_id).balance


def test_account_lifecycle(app, client):
    ids = prepare(app)
    login(client, "client1")

    # открытие нового счёта
    response = client.post("/accounts/open", data={"bank_id": ids["bank"],
                                                   "acc_type": ACC_CHECKING},
                           follow_redirects=True)
    assert "открыт" in response.get_data(as_text=True)
    with app.app_context():
        (db.session.query(Account)
         .filter_by(user_id=db.session.get(Account, ids["source"]).user_id)
         .order_by(Account.id.desc()).first())

    # блокировка менеджером
    client.post("/logout")
    login(client, "manager1")
    response = client.post(f"/manager/accounts/{ids['source']}/block", follow_redirects=True)
    assert "заблокирован" in response.get_data(as_text=True)

    # с заблокированного счёта перевод невозможен
    client.post("/logout")
    login(client, "client1")
    response = client.post("/transfer", data={"from_id": ids["source"], "to_id": ids["target"],
                                              "amount": "100"}, follow_redirects=True)
    assert "заблокирован" in response.get_data(as_text=True)

    # разблокировка возвращает возможность перевода
    client.post("/logout")
    login(client, "manager1")
    client.post(f"/manager/accounts/{ids['source']}/unblock")
    client.post("/logout")
    login(client, "client1")
    response = client.post("/transfer", data={"from_id": ids["source"], "to_id": ids["target"],
                                              "amount": "100"}, follow_redirects=True)
    assert "выполнен" in response.get_data(as_text=True)

    # закрыть счёт с остатком нельзя
    response = client.post(f"/accounts/{ids['source']}/close", follow_redirects=True)
    assert "нулевым балансом" in response.get_data(as_text=True)

    # переводим остаток и закрываем
    client.post("/transfer", data={"from_id": ids["source"], "to_id": ids["target"],
                                   "amount": "900"})
    response = client.post(f"/accounts/{ids['source']}/close", follow_redirects=True)
    assert "закрыт" in response.get_data(as_text=True)

    with app.app_context():
        assert db.session.get(Account, ids["source"]).is_closed is True
        assert balance(ids["target"]) == 1000.0

    # закрытый счёт не участвует в переводах
    response = client.post("/transfer", data={"from_id": ids["source"], "to_id": ids["target"],
                                              "amount": "1"}, follow_redirects=True)
    assert "закрыт" in response.get_data(as_text=True)

    # закрыть закрытый счёт повторно нельзя
    response = client.post(f"/accounts/{ids['source']}/close", follow_redirects=True)
    assert "уже закрыт" in response.get_data(as_text=True)

    # история закрытого счёта сохраняется
    response = client.get("/history")
    assert "перевод" in response.get_data(as_text=True)


def test_closed_account_hides_from_client_page(app, client):
    ids = prepare(app)
    login(client, "client1")
    with app.app_context():
        db.session.get(Account, ids["source"]).is_closed = True
        db.session.commit()

    response = client.get("/accounts")
    text = response.get_data(as_text=True)
    assert "закрыт" in text

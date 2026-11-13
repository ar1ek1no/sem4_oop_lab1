"""Интеграционные тесты страниц клиента: счета, переводы, вклады, история."""
from extensions import db
from models import ACC_CHECKING, ACC_SAVING, Account
from tests.factories import (
    create_account,
    create_bank,
    create_enterprise,
    create_user,
    login,
)


def prepare(app):
    """Клиент с двумя счетами, второй клиент и банк."""
    with app.app_context():
        bank = create_bank("МТБанк")
        second_bank = create_bank("Приорбанк")
        client = create_user("client1")
        other = create_user("client2")
        checking = create_account(client, bank, ACC_CHECKING, 1000.0)
        saving = create_account(client, bank, ACC_SAVING, 500.0)
        zero = create_account(client, second_bank, ACC_CHECKING, 0.0)
        foreign = create_account(other, bank, ACC_CHECKING, 100.0)
        return {"checking": checking.id, "saving": saving.id, "zero": zero.id,
                "foreign": foreign.id, "bank": bank.id, "second_bank": second_bank.id}


def test_accounts_page_lists_accounts(app, client):
    ids = prepare(app)
    login(client, "client1")

    response = client.get("/accounts")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "МТБанк" in text
    assert f"№{ids['checking']}" in text or str(ids["checking"]) in text


def test_open_account(app, client):
    ids = prepare(app)
    login(client, "client1")

    response = client.post("/accounts/open",
                           data={"bank_id": ids["bank"], "acc_type": ACC_SAVING},
                           follow_redirects=True)

    assert "открыт" in response.get_data(as_text=True)
    with app.app_context():
        accounts = db.session.query(Account).filter_by(acc_type=ACC_SAVING).all()
        assert len(accounts) == 2


def test_open_account_with_unknown_bank(app, client):
    prepare(app)
    login(client, "client1")

    response = client.post("/accounts/open", data={"bank_id": "999", "acc_type": ACC_CHECKING},
                           follow_redirects=True)

    assert "банк не найден" in response.get_data(as_text=True)


def test_open_account_with_invalid_type(app, client):
    ids = prepare(app)
    login(client, "client1")

    response = client.post("/accounts/open",
                           data={"bank_id": ids["bank"], "acc_type": "deposit"},
                           follow_redirects=True)

    assert "неизвестный тип счёта" in response.get_data(as_text=True)


def test_close_empty_account(app, client):
    ids = prepare(app)
    login(client, "client1")

    response = client.post(f"/accounts/{ids['zero']}/close", follow_redirects=True)
    assert "закрыт" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Account, ids["zero"]).is_closed is True


def test_close_account_with_balance_denied(app, client):
    ids = prepare(app)
    login(client, "client1")

    response = client.post(f"/accounts/{ids['checking']}/close", follow_redirects=True)

    assert "нулевым балансом" in response.get_data(as_text=True)


def test_close_foreign_account_denied(app, client):
    ids = prepare(app)
    login(client, "client1")

    response = client.post(f"/accounts/{ids['foreign']}/close", follow_redirects=True)

    assert "счёт не найден" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Account, ids["foreign"]).is_closed is False


def test_accumulate_savings(app, client):
    ids = prepare(app)
    login(client, "client1")

    client.post("/accounts/accumulate", follow_redirects=True)

    with app.app_context():
        assert db.session.get(Account, ids["saving"]).balance == 525.0
        assert db.session.get(Account, ids["checking"]).balance == 1000.0


def test_accumulate_without_savings(app, client):
    with app.app_context():
        bank = create_bank()
        user = create_user("poor")
        create_account(user, bank, ACC_CHECKING, 10.0)
    login(client, "poor")

    response = client.post("/accounts/accumulate", follow_redirects=True)
    assert "нет вкладов" in response.get_data(as_text=True)


def test_transfer_page_requires_two_accounts(app, client):
    with app.app_context():
        bank = create_bank()
        user = create_user("lonely")
        create_account(user, bank, ACC_CHECKING, 10.0)
    login(client, "lonely")

    response = client.get("/transfer")
    assert "Нужно минимум два открытых счёта" in response.get_data(as_text=True)


def test_transfer_success(app, client):
    ids = prepare(app)
    login(client, "client1")

    response = client.post("/transfer", data={"from_id": ids["checking"],
                                              "to_id": ids["saving"], "amount": "200"},
                           follow_redirects=True)

    assert "выполнен" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Account, ids["checking"]).balance == 800.0
        assert db.session.get(Account, ids["saving"]).balance == 700.0


def test_transfer_insufficient(app, client):
    ids = prepare(app)
    login(client, "client1")

    response = client.post("/transfer", data={"from_id": ids["checking"],
                                              "to_id": ids["saving"], "amount": "999999"},
                           follow_redirects=True)

    assert "недостаточно" in response.get_data(as_text=True)


def test_transfer_to_same_account(app, client):
    ids = prepare(app)
    login(client, "client1")

    response = client.post("/transfer", data={"from_id": ids["checking"],
                                              "to_id": ids["checking"], "amount": "10"},
                           follow_redirects=True)

    assert "тот же счёт" in response.get_data(as_text=True)


def test_transfer_from_foreign_account(app, client):
    ids = prepare(app)
    login(client, "client1")

    response = client.post("/transfer", data={"from_id": ids["foreign"],
                                              "to_id": ids["checking"], "amount": "10"},
                           follow_redirects=True)

    assert "счёт списания не найден" in response.get_data(as_text=True)


def test_transfer_invalid_amount(app, client):
    ids = prepare(app)
    login(client, "client1")

    response = client.post("/transfer", data={"from_id": ids["checking"],
                                              "to_id": ids["saving"], "amount": "abc"},
                           follow_redirects=True)

    assert "сумма должна быть числом" in response.get_data(as_text=True)


def test_transfer_from_closed_account(app, client):
    ids = prepare(app)
    with app.app_context():
        db.session.get(Account, ids["zero"]).is_closed = True
        db.session.commit()
    login(client, "client1")

    response = client.post("/transfer", data={"from_id": ids["zero"],
                                              "to_id": ids["checking"], "amount": "10"},
                           follow_redirects=True)

    assert "счёт списания закрыт" in response.get_data(as_text=True)


def test_salary_page_without_employment(app, client):
    prepare(app)
    with app.app_context():
        create_enterprise("EPAM")
    login(client, "client1")

    response = client.get("/salary")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "не в штате" in text
    assert "EPAM" in text


def test_salary_apply_creates_request(app, client):
    prepare(app)
    with app.app_context():
        enterprise = create_enterprise("EPAM")
        enterprise_id = enterprise.id
    login(client, "client1")

    response = client.post("/salary/apply", data={"enterprise_id": enterprise_id},
                           follow_redirects=True)

    assert "отправлена" in response.get_data(as_text=True)
    assert "ожидает решения" in response.get_data(as_text=True)


def test_salary_apply_twice(app, client):
    prepare(app)
    with app.app_context():
        enterprise = create_enterprise("EPAM")
        enterprise_id = enterprise.id
    login(client, "client1")

    client.post("/salary/apply", data={"enterprise_id": enterprise_id})
    response = client.post("/salary/apply", data={"enterprise_id": enterprise_id},
                           follow_redirects=True)

    assert "уже подана" in response.get_data(as_text=True)


def test_salary_pay_without_request_denied(app, client):
    ids = prepare(app)
    with app.app_context():
        create_enterprise("EPAM")
    login(client, "client1")

    response = client.post("/salary/pay",
                           data={"enterprise_id": 1, "account_id": ids["checking"]},
                           follow_redirects=True)

    assert "не являетесь сотрудником" in response.get_data(as_text=True)


def test_history_shows_transfer(app, client):
    ids = prepare(app)
    login(client, "client1")
    client.post("/transfer", data={"from_id": ids["checking"],
                                   "to_id": ids["saving"], "amount": "10"})

    response = client.get("/history")
    text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "перевод" in text
    assert "выполнено" in text


def test_history_empty_for_new_client(app, client):
    with app.app_context():
        create_user("empty")
    login(client, "empty")

    response = client.get("/history")
    assert "Операций пока нет" in response.get_data(as_text=True)


def test_client_cannot_open_manager_pages(app, client):
    prepare(app)
    login(client, "client1")

    for path in ("/manager/clients", "/manager/requests", "/manager/accounts",
                 "/manager/enterprises", "/manager/history", "/admin/logs"):
        assert client.get(path).status_code == 403


def test_unknown_page_404(app, client):
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert "Страница не найдена" in response.get_data(as_text=True)

"""Интеграционные тесты обработки ошибок (NFR-3): без стека, путей и SQL."""
from unittest.mock import patch

from tests.factories import api_headers, create_user


def test_404_page(app, client):
    response = client.get("/definitely-missing")
    assert response.status_code == 404
    text = response.get_data(as_text=True)
    assert "Страница не найдена" in text
    assert "Traceback" not in text


def test_404_api_is_json(client):
    response = client.get("/api/v1/definitely-missing")
    assert response.status_code == 404
    assert response.is_json
    assert "Traceback" not in response.get_data(as_text=True)


def test_405_uses_error_page(app, client):
    response = client.delete("/login")
    assert response.status_code == 405
    assert "Traceback" not in response.get_data(as_text=True)


def test_500_page_hides_details(app, client):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    with app.app_context():
        create_user("client1")
    client.post("/login", data={"username": "client1", "password": "secret123"})

    with patch("repositories.account_repository.AccountRepository.get_user_accounts",
               side_effect=RuntimeError("секретный SQL: SELECT * FROM users")):
        response = client.get("/accounts")

    text = response.get_data(as_text=True)
    assert response.status_code == 500
    assert "секретный SQL" not in text
    assert "Traceback" not in text
    assert "Что-то пошло не так" in text


def test_500_api_hides_details(app, client):
    app.config["PROPAGATE_EXCEPTIONS"] = False
    with app.app_context():
        create_user("manager1", role="manager")
    headers = api_headers(client, "manager1")

    with patch("services.manager_service.ManagerService.pending_clients",
               side_effect=RuntimeError("секретный SQL")):
        response = client.get("/api/v1/manager/clients", headers=headers)

    assert response.status_code == 500
    assert response.get_json()["error"] == "внутренняя ошибка сервера"
    assert "секретный SQL" not in response.get_data(as_text=True)


def test_validation_error_does_not_leak_stack(app, client):
    with app.app_context():
        create_user("client1")
    client.post("/login", data={"username": "client1", "password": "secret123"})

    response = client.post("/transfer", data={"from_id": "abc", "to_id": "x", "amount": "y"},
                           follow_redirects=True)
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Traceback" not in text
    assert "сумма должна быть числом" in text

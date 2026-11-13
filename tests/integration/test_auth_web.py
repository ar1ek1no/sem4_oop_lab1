"""Интеграционные тесты входа и регистрации через HTTP."""
from extensions import db
from models import ROLE_ADMIN, ROLE_CLIENT, User
from tests.factories import create_user, login


def test_login_page_available(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Вход в систему" in response.get_data(as_text=True)


def test_login_success_redirects_home(app, client):
    with app.app_context():
        create_user("client1")

    response = login(client, "client1")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_login_failure_shows_message(app, client):
    with app.app_context():
        create_user("client1")

    response = client.post("/login", data={"username": "client1", "password": "wrong"},
                           follow_redirects=True)

    assert response.status_code == 200
    assert "неверный логин или пароль" in response.get_data(as_text=True)


def test_login_pending_user_denied(app, client):
    with app.app_context():
        create_user("pending", approved=False)

    response = client.post("/login", data={"username": "pending", "password": "secret123"},
                           follow_redirects=True)

    assert "не подтверждена" in response.get_data(as_text=True)


def test_login_rejected_user_denied(app, client):
    with app.app_context():
        user = create_user("rejected", approved=False)
        user.is_rejected = True
        db.session.commit()

    response = client.post("/login", data={"username": "rejected", "password": "secret123"},
                           follow_redirects=True)

    assert "отклонена" in response.get_data(as_text=True)


def test_login_redirects_to_next(app, client):
    with app.app_context():
        create_user("client1")

    response = client.post("/login?next=/accounts",
                           data={"username": "client1", "password": "secret123"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/accounts")


def test_login_blocks_external_redirect(app, client):
    with app.app_context():
        create_user("client1")

    response = client.post("/login?next=//evil.example",
                           data={"username": "client1", "password": "secret123"})

    assert response.status_code == 302
    assert "evil" not in response.headers["Location"]


def test_register_creates_pending_client(app, client):
    response = client.post("/register", data={
        "username": "newbie", "password": "secret123", "full_name": "Новиков Пётр",
    }, follow_redirects=True)

    assert "менеджер" in response.get_data(as_text=True)
    with app.app_context():
        user = db.session.query(User).filter_by(username="newbie").first()
        assert user is not None
        assert user.role == ROLE_CLIENT
        assert user.is_approved is False
        assert user.full_name == "Новиков Пётр"


def test_register_ignores_role_from_form(app, client):
    client.post("/register", data={
        "username": "hacker", "password": "secret123", "full_name": "Хакеров Иван",
        "role": ROLE_ADMIN,
    })
    with app.app_context():
        user = db.session.query(User).filter_by(username="hacker").first()
        assert user.role == ROLE_CLIENT


def test_register_validation_errors(app, client):
    response = client.post("/register", data={
        "username": "ab", "password": "1", "full_name": "",
    })

    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "логин короче" in text
    assert "пароль короче" in text
    assert "укажите ФИО" in text


def test_register_duplicate_login(app, client):
    with app.app_context():
        create_user("taken")

    response = client.post("/register", data={
        "username": "taken", "password": "secret123", "full_name": "Иванов Иван",
    }, follow_redirects=True)

    assert "занят" in response.get_data(as_text=True)


def test_logout_clears_session(app, client):
    with app.app_context():
        create_user("client1")
    login(client, "client1")

    response = client.post("/logout", follow_redirects=False)
    assert response.status_code == 302

    response = client.get("/accounts")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logout_by_link(app, client):
    with app.app_context():
        create_user("client1")
    login(client, "client1")
    assert client.get("/logout").status_code == 302


def test_logged_in_user_redirected_from_login(app, client):
    with app.app_context():
        create_user("client1")
    login(client, "client1")

    response = client.get("/login")
    assert response.status_code == 302


def test_role_redirect_home(app, client):
    with app.app_context():
        create_user("manager", role="manager")
    login(client, "manager")
    response = client.get("/")
    assert response.headers["Location"].endswith("/manager/clients")


def test_anonymous_home_redirects_to_login(client):
    response = client.get("/")
    assert response.headers["Location"].endswith("/login")

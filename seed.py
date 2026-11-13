"""Демо-данные: банки, предприятия, учётные записи трёх ролей.

Запуск: `python seed.py`. Скрипт идемпотентен — повторный запуск ничего не дублирует.
"""
from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models import (
    ACC_CHECKING,
    ACC_SAVING,
    ROLE_ADMIN,
    ROLE_CLIENT,
    ROLE_MANAGER,
    Account,
    Bank,
    Enterprise,
    User,
)

BANKS = ["МТБанк", "БНБ-Банк", "Беларусбанк", "Приорбанк", "Альфа-Банк", "Технобанк"]
ENTERPRISES = ["EPAM", "Wargaming", "МАЗ", "МТЗ", "IT-Academy", "Белтелеком"]

# логин, пароль, ФИО, роль, подтверждён
USERS = [
    ("client1", "client1", "Иванова Мария Сергеевна", ROLE_CLIENT, True),
    ("client2", "client2", "Петров Иван Олегович", ROLE_CLIENT, True),
    ("client3", "client3", "Сидорова Анна Павловна", ROLE_CLIENT, False),
    ("manager1", "manager1", "Ковалёв Сергей Игоревич", ROLE_MANAGER, True),
    ("admin1", "admin1", "Орлова Елена Викторовна", ROLE_ADMIN, True),
]


def setup(app=None) -> None:
    app = app or create_app()
    with app.app_context():
        db.create_all()

        for name in BANKS:
            if db.session.query(Bank).filter_by(name=name).first() is None:
                db.session.add(Bank(name=name))

        for name in ENTERPRISES:
            if db.session.query(Enterprise).filter_by(name=name).first() is None:
                db.session.add(Enterprise(name=name))

        for username, password, full_name, role, approved in USERS:
            if db.session.query(User).filter_by(username=username).first() is not None:
                continue
            db.session.add(User(
                username=username,
                password_hash=generate_password_hash(password),
                full_name=full_name,
                role=role,
                is_approved=approved,
            ))

        db.session.commit()

        client = db.session.query(User).filter_by(username="client1").first()
        banks = db.session.query(Bank).order_by(Bank.id).all()
        if client is not None and banks and not client.accounts:
            db.session.add(Account(user_id=client.id, bank_id=banks[0].id,
                                   acc_type=ACC_CHECKING, balance=5000.0))
            db.session.add(Account(user_id=client.id, bank_id=banks[2].id,
                                   acc_type=ACC_SAVING, balance=1000.0))
            db.session.commit()

        print("демо-данные готовы")
        print("клиент:   client1 / client1")
        print("менеджер: manager1 / manager1")
        print("админ:    admin1 / admin1")


if __name__ == "__main__":
    setup()

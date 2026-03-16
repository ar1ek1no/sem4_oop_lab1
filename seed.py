from models import session, User, Bank, Enterprise, init_db


def setup():
    init_db()

    if not session.query(User).filter_by(username="admin").first():
        session.add(User(username="myadmin", password="123", role="admin", is_approved=True))
    if not session.query(User).filter_by(username="m1").first():
        session.add(User(username="mymanager", password="123", role="manager", is_approved=True))

    banks = ["МТБанк", "БНБ-Банк", "Беларусбанк", "Приорбанк", "Альфа-Банк", "Технобанк"]
    for b_name in banks:
        if not session.query(Bank).filter_by(name=b_name).first():
            session.add(Bank(name=b_name))

    ents = ["EPAM", "Wargaming", "МАЗ", "МТЗ", "IT-Academy", "Белтелеком"]
    for e_name in ents:
        if not session.query(Enterprise).filter_by(name=e_name).first():
            session.add(Enterprise(name=e_name))

    session.commit()
    print("база заполнена")


if __name__ == "__main__":
    setup()

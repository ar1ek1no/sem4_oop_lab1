from models import session, User

class UserRepository:
    @staticmethod
    def create_user(username, password, role):
        approved_status = True if role in ['admin', 'manager'] else False
        new_user = User(
            username=username,
            password=password,
            role=role,
            is_approved=approved_status
        )
        session.add(new_user)
        session.commit()
        return new_user

    @staticmethod
    def get_user_by_username(username: str):
        return session.query(User).filter(User.username == username).first()

    @staticmethod
    def get_user_by_id(user_id: int):
        return session.query(User).get(user_id)

    @staticmethod
    def get_pending_users():
        return session.query(User).filter(User.is_approved == False).all()

    @staticmethod
    def approve_user(user_id: int):
        user = session.query(User).get(user_id)
        if user:
            user.is_approved = True
            session.commit()
            return True
        return False

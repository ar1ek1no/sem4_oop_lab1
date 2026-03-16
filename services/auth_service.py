from repositories.user_repository import UserRepository


class AuthService:
    _current_user = None

    @staticmethod
    def register(username, password, role):
        if len(username) < 3 or len(password) < 3:
            return False, "слишком короткий логин или пароль (try to gatekeep)"
        if UserRepository.get_user_by_username(username):
            return False, "пользователь уже существует"
        UserRepository.create_user(username, password, role)
        return True, "регистрация успешна! ждем подтверждения менеджером"

    @staticmethod
    def login(username, password):
        user = UserRepository.get_user_by_username(username)
        if user and user.password == password:
            if not user.is_approved:
                return False, "ваш аккаунт еще не подтвержден!"
            AuthService._current_user = user
            return True, user
        return False, "неверный логин или пароль (copycat bruh)"

    @staticmethod
    def logout():
        AuthService._current_user = None

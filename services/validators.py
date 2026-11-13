"""Проверка пользовательского ввода.

Все проверки — серверные: форму можно обойти, сервер — нет. Возвращаем текст ошибки
или None, чтобы вызывающий код не разбирал исключения.
"""
import math
from decimal import Decimal, InvalidOperation

USERNAME_MIN = 3
USERNAME_MAX = 80
PASSWORD_MIN = 6
PASSWORD_MAX = 128
FULL_NAME_MIN = 2
FULL_NAME_MAX = 200
AMOUNT_MIN = 0.01
AMOUNT_MAX = 1_000_000.0


def check_username(username: str) -> str | None:
    value = (username or "").strip()
    if not value:
        return "логин не может быть пустым"
    if len(value) < USERNAME_MIN:
        return f"логин короче {USERNAME_MIN} символов"
    if len(value) > USERNAME_MAX:
        return f"логин длиннее {USERNAME_MAX} символов"
    if not all(ch.isalnum() or ch in "_.-" for ch in value):
        return "в логине допустимы буквы, цифры и символы _ . -"
    return None


def check_password(password: str) -> str | None:
    value = password or ""
    if not value:
        return "пароль не может быть пустым"
    if len(value) < PASSWORD_MIN:
        return f"пароль короче {PASSWORD_MIN} символов"
    if len(value) > PASSWORD_MAX:
        return f"пароль длиннее {PASSWORD_MAX} символов"
    return None


def check_full_name(full_name: str) -> str | None:
    value = (full_name or "").strip()
    if not value:
        return "укажите ФИО"
    if len(value) < FULL_NAME_MIN:
        return "ФИО слишком короткое"
    if len(value) > FULL_NAME_MAX:
        return "ФИО слишком длинное"
    return None


def parse_amount(raw) -> tuple[float | None, str | None]:
    """Строка из формы → сумма. Принимает «100», «100.50», «100,50», «1 000»."""
    if raw is None:
        return None, "укажите сумму"
    text = str(raw).strip().replace(" ", "").replace(",", ".")
    if not text:
        return None, "укажите сумму"
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None, "сумма должна быть числом"
    if not amount.is_finite():
        return None, "сумма должна быть числом"
    value = float(amount)
    if value < AMOUNT_MIN:
        return None, f"сумма должна быть больше {AMOUNT_MIN}"
    if value > AMOUNT_MAX:
        return None, f"сумма не может превышать {AMOUNT_MAX:,.0f}".replace(",", " ")
    return round(value, 2), None


def check_amount_value(amount: float) -> str | None:
    """Проверка суммы, пришедшей не из формы (API, тесты, вызов сервиса)."""
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        return "сумма должна быть числом"
    if math.isnan(amount) or math.isinf(amount):
        return "сумма должна быть числом"
    if amount < AMOUNT_MIN:
        return f"сумма должна быть больше {AMOUNT_MIN}"
    if amount > AMOUNT_MAX:
        return f"сумма не может превышать {AMOUNT_MAX:,.0f}".replace(",", " ")
    return None


def format_money(value: float) -> str:
    """Деньги в интерфейсе: 1234.5 → «1 234.50 BYN»."""
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " BYN"

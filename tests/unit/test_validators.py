"""Юнит-тесты проверки ввода: границы, негативные случаи, параметризация."""
import pytest

from services.validators import (
    AMOUNT_MAX,
    AMOUNT_MIN,
    PASSWORD_MIN,
    check_amount_value,
    check_full_name,
    check_password,
    check_username,
    format_money,
    parse_amount,
)


class TestCheckUsername:
    @pytest.mark.parametrize("username", ["abc", "user_1", "a.b-c", "Клиент1"])
    def test_valid(self, username):
        assert check_username(username) is None

    @pytest.mark.parametrize("username", ["", "   ", None, "ab"])
    def test_empty_or_short(self, username):
        assert check_username(username) is not None

    @pytest.mark.parametrize("username", ["user name", "user!", "a" * 81])
    def test_invalid_characters_or_length(self, username):
        assert check_username(username) is not None


class TestCheckPassword:
    def test_valid(self):
        assert check_password("s" * PASSWORD_MIN) is None

    @pytest.mark.parametrize("password", ["", None, "12345"])
    def test_too_short(self, password):
        assert check_password(password) is not None

    def test_too_long(self):
        assert check_password("x" * 129) is not None


class TestCheckFullName:
    @pytest.mark.parametrize("name", ["Иванов Иван", "Ян", "Иванова Мария Сергеевна"])
    def test_valid(self, name):
        assert check_full_name(name) is None

    @pytest.mark.parametrize("name", ["", "   ", None, "x" * 201])
    def test_invalid(self, name):
        assert check_full_name(name) is not None


class TestParseAmount:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("100", 100.0), ("100.50", 100.5), ("100,50", 100.5), ("1 000", 1000.0), ("0.01", 0.01)],
    )
    def test_valid(self, raw, expected):
        amount, error = parse_amount(raw)
        assert error is None
        assert amount == expected

    @pytest.mark.parametrize("raw", ["", None, "abc", "-5", "0", "0.001", "nan", "inf"])
    def test_invalid(self, raw):
        amount, error = parse_amount(raw)
        assert amount is None
        assert error

    def test_max_boundary(self):
        assert parse_amount(str(AMOUNT_MAX))[1] is None
        assert parse_amount(str(AMOUNT_MAX + 1))[1] is not None

    def test_min_boundary(self):
        assert parse_amount(str(AMOUNT_MIN))[1] is None
        assert parse_amount("0.001")[1] is not None


class TestCheckAmountValue:
    @pytest.mark.parametrize("amount", [0.01, 100, AMOUNT_MAX])
    def test_valid(self, amount):
        assert check_amount_value(amount) is None

    @pytest.mark.parametrize("amount", [0, -1, AMOUNT_MAX + 1, "100", None, True, float("nan")])
    def test_invalid(self, amount):
        assert check_amount_value(amount) is not None


def test_format_money():
    assert format_money(1234.5) == "1 234,50 BYN"
    assert format_money(0) == "0,00 BYN"

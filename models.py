"""Модели предметной области.

Слой данных ничего не знает про Flask: только таблицы, связи и допустимые значения.
Строковые константы вместо «магических» значений — их используют сервисы, шаблоны и тесты.
"""
from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint

from extensions import db


def utcnow() -> datetime:
    """Наивное UTC-время: SQLite не хранит часовой пояс."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --- Роли (FR-4) ---
ROLE_CLIENT = "client"
ROLE_MANAGER = "manager"
ROLE_ADMIN = "admin"
ROLES = (ROLE_CLIENT, ROLE_MANAGER, ROLE_ADMIN)
ROLE_TITLES = {ROLE_CLIENT: "клиент", ROLE_MANAGER: "менеджер", ROLE_ADMIN: "администратор"}

# --- Типы счетов (FR-6, FR-11) ---
ACC_CHECKING = "checking"
ACC_SAVING = "saving"
ACCOUNT_TYPES = (ACC_CHECKING, ACC_SAVING)
ACCOUNT_TYPE_TITLES = {ACC_CHECKING: "счёт", ACC_SAVING: "вклад"}
DEPOSIT_RATE = 0.05  # 5 % годовых по вкладу

# --- Статусы заявки на зарплатный проект (жизненный цикл, см. docs/STATE_DIAGRAM.md) ---
REQ_PENDING = "pending"
REQ_APPROVED = "approved"
REQ_REJECTED = "rejected"
REQUEST_STATUSES = (REQ_PENDING, REQ_APPROVED, REQ_REJECTED)
REQUEST_STATUS_TITLES = {
    REQ_PENDING: "ожидает решения",
    REQ_APPROVED: "подтверждена",
    REQ_REJECTED: "отклонена",
}

# --- Статусы записи журнала ---
LOG_COMPLETED = "completed"
LOG_CANCELLED = "cancelled"

# --- Типы действий (используются командами отмены) ---
ACTION_OPEN_ACCOUNT = "open_acc"
ACTION_CLOSE_ACCOUNT = "close_acc"
ACTION_TRANSFER = "transfer"
ACTION_SALARY = "salary"
ACTION_ACCUMULATE = "accumulate"
ACTION_APPROVE_USER = "approve_user"
ACTION_REJECT_USER = "reject_user"
ACTION_APPROVE_SALARY = "approve_salary"
ACTION_REJECT_SALARY = "reject_salary"
ACTION_APPLY_SALARY = "apply_salary"
ACTION_REVOKE_SALARY = "revoke_salary"
ACTION_FIRE_EMPLOYEE = "fire_employee"
ACTION_BLOCK = "block"
ACTION_UNBLOCK = "unblock"
ACTION_UNDO = "undo"

ACTION_TITLES = {
    ACTION_OPEN_ACCOUNT: "открытие счёта",
    ACTION_CLOSE_ACCOUNT: "закрытие счёта",
    ACTION_TRANSFER: "перевод",
    ACTION_SALARY: "выплата зарплаты",
    ACTION_ACCUMULATE: "начисление процентов",
    ACTION_APPROVE_USER: "подтверждение клиента",
    ACTION_REJECT_USER: "отклонение клиента",
    ACTION_APPROVE_SALARY: "подтверждение заявки",
    ACTION_REJECT_SALARY: "отклонение заявки",
    ACTION_APPLY_SALARY: "подача заявки",
    ACTION_REVOKE_SALARY: "отзыв подтверждения",
    ACTION_FIRE_EMPLOYEE: "увольнение",
    ACTION_BLOCK: "блокировка счёта",
    ACTION_UNBLOCK: "разблокировка счёта",
    ACTION_UNDO: "отмена действия",
}

DEFAULT_SALARY = 1000.0


class User(db.Model):
    """Пользователь: клиент, менеджер или администратор."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(200), nullable=False, default="")
    role = db.Column(db.String(20), nullable=False, default=ROLE_CLIENT)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    # отклонённая регистрация: войти нельзя, но запись остаётся — отмену можно откатить
    is_rejected = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    accounts = db.relationship("Account", back_populates="owner", lazy="selectin")
    enterprises = db.relationship(
        "Enterprise", secondary="employment", back_populates="employees", lazy="selectin",
    )

    @property
    def is_client(self) -> bool:
        return self.role == ROLE_CLIENT

    @property
    def is_manager(self) -> bool:
        return self.role == ROLE_MANAGER

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def role_title(self) -> str:
        return ROLE_TITLES.get(self.role, self.role)

    def __repr__(self) -> str:  # pragma: no cover - отладка
        return f"<User {self.username} {self.role}>"


class Bank(db.Model):
    """Банк, в котором клиент открывает счёт."""

    __tablename__ = "banks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - отладка
        return f"<Bank {self.name}>"


class Enterprise(db.Model):
    """Предприятие, которое платит зарплату через платформу."""

    __tablename__ = "enterprises"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    employees = db.relationship(
        "User", secondary="employment", back_populates="enterprises", lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - отладка
        return f"<Enterprise {self.name}>"


class Employment(db.Model):
    """Сотрудник предприятия: связь многие-ко-многим с окладом и датой приёма."""

    __tablename__ = "employment"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    enterprise_id = db.Column(db.Integer, db.ForeignKey("enterprises.id"), primary_key=True)
    salary_amount = db.Column(db.Float, nullable=False, default=DEFAULT_SALARY)
    hired_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id], overlaps="employees,enterprises")
    enterprise = db.relationship(
        "Enterprise", foreign_keys=[enterprise_id], overlaps="employees,enterprises",
    )


class Account(db.Model):
    """Счёт или вклад клиента."""

    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    bank_id = db.Column(db.Integer, db.ForeignKey("banks.id"), nullable=False, index=True)
    balance = db.Column(db.Float, default=0.0, nullable=False)
    acc_type = db.Column(db.String(20), nullable=False, default=ACC_CHECKING)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)
    # закрытый счёт остаётся в БД: история и отмена закрытия сохраняются
    is_closed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    owner = db.relationship("User", back_populates="accounts")
    bank = db.relationship("Bank")

    @property
    def type_title(self) -> str:
        return ACCOUNT_TYPE_TITLES.get(self.acc_type, self.acc_type)

    @property
    def display_name(self) -> str:
        return f"{self.type_title} №{self.id} ({self.bank.name if self.bank else '—'})"

    @property
    def is_saving(self) -> bool:
        return self.acc_type == ACC_SAVING

    @property
    def is_active(self) -> bool:
        return not self.is_closed


class TransactionLog(db.Model):
    """Журнал действий: и для истории клиента, и для отмены администратором (FR-15)."""

    __tablename__ = "transaction_logs"

    id = db.Column(db.Integer, primary_key=True)
    sender_acc_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=True, index=True)
    receiver_acc_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=True, index=True)
    amount = db.Column(db.Float, default=0.0, nullable=False)
    action_type = db.Column(db.String(40), nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    status = db.Column(db.String(20), default=LOG_COMPLETED, nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    # Структурированные данные действия: команда отмены читает их, а не «чужие» поля
    payload = db.Column(db.JSON, nullable=True)

    sender = db.relationship("Account", foreign_keys=[sender_acc_id])
    receiver = db.relationship("Account", foreign_keys=[receiver_acc_id])
    actor = db.relationship("User", foreign_keys=[actor_id])

    @property
    def action_title(self) -> str:
        return ACTION_TITLES.get(self.action_type, self.action_type)


class SalaryRequest(db.Model):
    """Заявка на зарплатный проект: сущность с жизненным циклом."""

    __tablename__ = "salary_requests"
    __table_args__ = (UniqueConstraint("user_id", "enterprise_id", "status", name="uq_request_state"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    enterprise_id = db.Column(db.Integer, db.ForeignKey("enterprises.id"), nullable=False, index=True)
    status = db.Column(db.String(20), default=REQ_PENDING, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    last_paid_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User")
    enterprise = db.relationship("Enterprise")

    @property
    def status_title(self) -> str:
        return REQUEST_STATUS_TITLES.get(self.status, self.status)

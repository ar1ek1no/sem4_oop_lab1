from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

Base = declarative_base()


class Employment(Base):
    __tablename__ = 'employment'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    enterprise_id = Column(Integer, ForeignKey('enterprises.id'), primary_key=True)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'client', 'manager', 'admin'
    is_approved = Column(Boolean, default=False)

    accounts = relationship("Account", back_populates="owner")
    # связь с предприятиями через таблицу-посредник
    enterprises = relationship("Enterprise", secondary='employment', back_populates="employees")


class Bank(Base):
    __tablename__ = 'banks'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class Enterprise(Base):
    __tablename__ = 'enterprises'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    employees = relationship("User", secondary='employment', back_populates="enterprises")


class Account(Base):
    __tablename__ = 'accounts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    bank_id = Column(Integer, ForeignKey('banks.id'))
    balance = Column(Float, default=0.0)
    acc_type = Column(String)  # 'checking' (счет), 'saving' (вклад)
    is_blocked = Column(Boolean, default=False)

    owner = relationship("User", back_populates="accounts")


# табличка логов, транзакций (<- админ, менеджер)
class TransactionLog(Base):
    __tablename__ = 'transaction_logs'
    id = Column(Integer, primary_key=True)
    sender_acc_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    receiver_acc_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    amount = Column(Float)
    action_type = Column(String)  # 'transfer', 'open_acc', 'salary', 'block', 'unblock', 'fire_employee'
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default='completed')
    # хранить ID предприятия или ID юзера для отмены действий
    target_id = Column(Integer, nullable=True)

# заявки на зарплатные проекты
class SalaryRequest(Base):
    __tablename__ = 'salary_requests'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    enterprise_id = Column(Integer, ForeignKey('enterprises.id'))
    status = Column(String, default='pending')  # 'pending', 'approved', 'rejected'


# настройка
engine = create_engine('sqlite:///finance.db')
def init_db():
    Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

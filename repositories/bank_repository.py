from models import Bank, session

class BankRepository(Bank):
    @staticmethod
    def get_all_banks():
        return session.query(Bank).all()
    @staticmethod
    def get_bank_by_id(id):
        return session.query(Bank).filter(Bank.id == id).first()
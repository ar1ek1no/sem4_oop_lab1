from models import session, Enterprise

class EnterpriseRepository:
    @staticmethod
    def get_all_enterprises():
        return session.query(Enterprise).all()

    @staticmethod
    def get_enterprise_by_id(ent_id: int):
        return session.query(Enterprise).filter(Enterprise.id == ent_id).first()

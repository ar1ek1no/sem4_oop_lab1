from models import session, User, Enterprise, Account, TransactionLog, SalaryRequest, Employment


class ManagerService:
    @staticmethod
    def approve_client(user_id):
        u = session.query(User).get(user_id)
        if u:
            u.is_approved = True
            log = TransactionLog(action_type='approve_user', target_id=user_id, amount=0)
            session.add(log)
            session.commit()

    @staticmethod
    def get_pending_salaries(): # список неподтвержденных зарплат
        return session.query(SalaryRequest).filter_by(status='pending').all()

    @staticmethod
    def approve_salary_project(request_id):
        req = session.query(SalaryRequest).get(request_id)
        if req:
            req.status = 'approved'
            emp = Employment(user_id=req.user_id, enterprise_id=req.enterprise_id)
            session.add(emp)
            log = TransactionLog(action_type='approve_salary', target_id=req.user_id, amount=req.enterprise_id)
            session.add(log)
            session.commit()
            return True
        return False

    @staticmethod
    def toggle_block_account(acc_id): # управление статусом аккаунта
        acc = session.query(Account).get(acc_id)
        if acc:
            acc.is_blocked = not acc.is_blocked
            action = 'block' if acc.is_blocked else 'unblock'
            log = TransactionLog(receiver_acc_id=acc.id, action_type=action, amount=0)
            session.add(log)
            session.commit()
            return True
        return False

    @staticmethod
    def remove_employee(user_id, enterprise_id):
        emp = session.query(Employment).filter_by(user_id=user_id, enterprise_id=enterprise_id).first()
        if emp:
            session.delete(emp)
            # target_id = id предприятия, receiver_acc_id = id юзера!!!
            log = TransactionLog(action_type='fire_employee', target_id=enterprise_id, amount=user_id)
            session.add(log)
            session.commit()
            return True
        return False

    @staticmethod
    def get_user_transaction_history(user_id):
        from repositories.account_repository import AccountRepository
        acc_ids = [a.id for a in AccountRepository.get_user_accounts(user_id)]
        return session.query(TransactionLog).filter(
            (TransactionLog.sender_acc_id.in_(acc_ids)) |
            (TransactionLog.receiver_acc_id.in_(acc_ids))
        ).order_by(TransactionLog.timestamp.desc()).all()

    @staticmethod
    def get_all_accounts():
        return session.query(Account).all()

    @staticmethod
    def get_all_enterprises():
        return session.query(Enterprise).all()


class AdminService:
    @staticmethod
    def get_all_logs():
        return session.query(TransactionLog).order_by(TransactionLog.timestamp.desc()).all()

    @staticmethod
    def undo_transaction(log_id):
        log = session.query(TransactionLog).get(log_id)
        if not log or log.status == 'cancelled':
            return False, "невозможно отменить"

        try:
            # 1) отмена подтверждения юзера
            if log.action_type == 'approve_user':
                user = session.query(User).get(log.target_id)
                if user:
                    user.is_approved = False

            # 2) отмена одобрения зарплаты + увольнение (по сути) НО ВОЗВРАЩЕНИЕ ЗАЯВКИ
            elif log.action_type == 'approve_salary':
                # target_id = user_id, amount = enterprise_id (вспоминаем...)
                u_id = log.target_id
                e_id = int(log.amount)
                emp = session.query(Employment).filter_by(user_id=u_id, enterprise_id=e_id).first()
                if emp:
                    session.delete(emp)
                # обратно статус "pending"
                req = session.query(SalaryRequest).filter_by(user_id=u_id, enterprise_id=e_id).first()
                if req:
                    req.status = 'pending'
            # 3) отмена транзакции
            elif log.action_type == 'transfer':
                s_acc = session.query(Account).get(log.sender_acc_id)
                r_acc = session.query(Account).get(log.receiver_acc_id)
                if s_acc and r_acc:
                    s_acc.balance += log.amount
                    r_acc.balance -= log.amount

            # 4) отмена открытия счета
            elif log.action_type == 'open_acc':
                acc = session.query(Account).get(log.receiver_acc_id)
                if acc:
                    if acc.balance == 0:
                        session.delete(acc)
                    else:
                        return False, "нельзя удалить счет с балансом > 0"

            # 5) отмена получения зарплаты
            elif log.action_type == 'salary':
                acc = session.query(Account).get(log.receiver_acc_id)
                if acc:
                    acc.balance -= log.amount

            # 6) отмена блока/разблока
            elif log.action_type == 'block':
                acc = session.query(Account).get(log.receiver_acc_id)
                if acc: acc.is_blocked = False
            elif log.action_type == 'unblock':
                acc = session.query(Account).get(log.receiver_acc_id)
                if acc: acc.is_blocked = True

            # 7) увольнение
            elif log.action_type == 'fire_employee':
                user_id = int(log.amount)  # сохраняли id юзера сюда
                ent_id = log.target_id
                new_emp = Employment(user_id=user_id, enterprise_id=ent_id)
                session.add(new_emp)

            log.status = 'cancelled'
            session.commit()
            return True, f"действие '{log.action_type}' успешно отменено"

        except Exception as e:
            session.rollback()
            return False, f"ошибка при отмене (fallback): {str(e)}"

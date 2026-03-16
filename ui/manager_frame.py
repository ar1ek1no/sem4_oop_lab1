import customtkinter as ctk
from tkinter import messagebox
from services.admin_service import ManagerService
from repositories.user_repository import UserRepository
from repositories.enterprise_repository import EnterpriseRepository

class ManagerFrame(ctk.CTkFrame):
    def __init__(self, master, user, on_logout):
        super().__init__(master)
        self.user = user
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self.tab_reg = self.tabs.add("регистрации (new bees)")
        self.tab_sal = self.tabs.add("зарплаты (big leagues)")
        self.tab_accs = self.tabs.add("счета/история")
        self.tab_staff = self.tabs.add("компании и штат (landlord save us)")
        self.refresh_all()

    def refresh_all(self):
        self.draw_reg()
        self.draw_salaries()
        self.draw_accounts()
        self.draw_staff()

    def draw_reg(self):
        for w in self.tab_reg.winfo_children(): w.destroy()
        pending = UserRepository.get_pending_users()
        for u in pending:
            f = ctk.CTkFrame(self.tab_reg)
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=f"юзер: {u.username}").pack(side="left", padx=10)
            ctk.CTkButton(f, text="одобрить", width=80,
                          command=lambda uid=u.id: [ManagerService.approve_client(uid), self.refresh_all()]).pack(side="right", padx=5)

    def draw_salaries(self):
        for w in self.tab_sal.winfo_children(): w.destroy()
        requests = ManagerService.get_pending_salaries()
        for req in requests:
            user = UserRepository.get_user_by_id(req.user_id)
            ent = EnterpriseRepository.get_enterprise_by_id(req.enterprise_id)
            f = ctk.CTkFrame(self.tab_sal)
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=f"{user.username} -> {ent.name}").pack(side="left", padx=10)
            ctk.CTkButton(f, text="одобрить зп + зачислить на предприятие", width=100,
                          command=lambda rid=req.id: [ManagerService.approve_salary_project(rid), self.refresh_all()]).pack(side="right", padx=5)

    def draw_accounts(self):
        for w in self.tab_accs.winfo_children(): w.destroy()

        # Секция поиска истории
        search_f = ctk.CTkFrame(self.tab_accs)
        search_f.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(search_f, text="история юзера (id):").pack(side="left", padx=5)
        self.user_id_ent = ctk.CTkEntry(search_f, width=100)
        self.user_id_ent.pack(side="left", padx=5)
        ctk.CTkButton(search_f, text="показать историю", width=120, command=self.show_user_history).pack(side="left")

        scroll = ctk.CTkScrollableFrame(self.tab_accs)
        scroll.pack(fill="both", expand=True, pady=5)

        accs = ManagerService.get_all_accounts()
        for a in accs:
            owner = UserRepository.get_user_by_id(a.user_id)
            f = ctk.CTkFrame(scroll)
            f.pack(fill="x", pady=2)

            status = "БЛОК" if a.is_blocked else "НЕБЛОК"
            txt = f"ID:{a.id} | {owner.username} (UID:{owner.id}) | {a.balance} BYN | {status}"
            ctk.CTkLabel(f, text=txt).pack(side="left", padx=10)

            btn_txt = "разблок." if a.is_blocked else "заблокировать"
            ctk.CTkButton(f, text=btn_txt, width=120, fg_color=("red" if not a.is_blocked else "green"),
                          command=lambda aid=a.id: [ManagerService.toggle_block_account(aid), self.refresh_all()]).pack(
                side="right", padx=5)

    def draw_staff(self):
        for w in self.tab_staff.winfo_children(): w.destroy()
        ents = ManagerService.get_all_enterprises()
        scroll = ctk.CTkScrollableFrame(self.tab_staff)
        scroll.pack(fill="both", expand=True)

        for e in ents:
            f = ctk.CTkFrame(scroll)
            f.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(f, text=f"компания: {e.name}", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)

            for emp in e.employees:
                row = ctk.CTkFrame(f, fg_color="transparent")
                row.pack(fill="x", padx=20)
                ctk.CTkLabel(row, text=f"• {emp.username} (ID: {emp.id})").pack(side="left")
                ctk.CTkButton(row, text="уволить (sad..)", width=70, height=20, fg_color="brown",
                              command=lambda uid=emp.id, eid=e.id: self.fire_emp(uid, eid)).pack(side="right")

    def show_user_history(self):
        uid = self.user_id_ent.get()
        if not uid.isdigit(): return

        logs = ManagerService.get_user_transaction_history(int(uid))
        win = ctk.CTkToplevel(self)
        win.title(f"история пользователя {uid}")
        win.geometry("500x400")

        st = ctk.CTkScrollableFrame(win)
        st.pack(fill="both", expand=True, padx=10, pady=10)

        for l in logs:
            txt = f"{l.timestamp.strftime('%d.%m %H:%M')} | {l.action_type} | {l.amount} BYN.\nот:{l.sender_acc_id}, кому:{l.receiver_acc_id}"
            ctk.CTkLabel(st, text=txt, justify="left").pack(fill="x", pady=2)

    def fire_emp(self, uid, eid):
        if ManagerService.remove_employee(uid, eid):
            messagebox.showinfo("ок", "сотрудник удален из штата")
            self.refresh_all()
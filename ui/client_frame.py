import customtkinter as ctk
from tkinter import messagebox
from repositories.account_repository import AccountRepository
from repositories.bank_repository import BankRepository
from repositories.enterprise_repository import EnterpriseRepository
from services.bank_service import BankService


class ClientFrame(ctk.CTkFrame):
    def __init__(self, master, user, on_logout):
        super().__init__(master)
        self.user = user
        self.on_logout = on_logout

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_accs = self.tabs.add("счета и вклады")
        self.tab_transfers = self.tabs.add("переводы")
        self.tab_salary = self.tabs.add("работа + зп + aura")
        self.tab_history = self.tabs.add("история")

        self.setup_accounts_tab()
        self.setup_transfers_tab()
        self.setup_salary_tab()
        self.setup_history_tab()
        # загрузка апдейта
        self.update_transfer_combos()
        self.update_salary_combo()

    def setup_accounts_tab(self):
        self.acc_container = ctk.CTkScrollableFrame(self.tab_accs)
        self.acc_container.pack(fill="both", expand=True, side="left", padx=5)
        side_panel = ctk.CTkFrame(self.tab_accs, width=200)
        side_panel.pack(fill="y", side="right", padx=5)
        ctk.CTkLabel(side_panel, text="открыть новый:").pack(pady=10)
        banks = [b.name for b in BankRepository.get_all_banks()]
        self.bank_sel = ctk.CTkComboBox(side_panel, values=banks)
        self.bank_sel.pack(pady=5)
        self.type_sel = ctk.CTkComboBox(side_panel, values=["счет?", "вклад?"])
        self.type_sel.pack(pady=5)
        ctk.CTkButton(side_panel, text="открыть", command=self.open_acc).pack(pady=10)
        ctk.CTkButton(side_panel, text="накопление (+5%)", fg_color="orange", command=self.do_accumulate).pack(pady=20)
        self.refresh_accounts()

    def refresh_accounts(self):
        for w in self.acc_container.winfo_children(): w.destroy()
        accs = AccountRepository.get_user_accounts(self.user.id)
        for acc in accs:
            f = ctk.CTkFrame(self.acc_container)
            f.pack(fill="x", pady=2)
            bank = BankRepository.get_bank_by_id(acc.bank_id)
            status = " [БЛОКИРОВАН]" if acc.is_blocked else ""
            txt = f"{acc.acc_type.upper()} | {bank.name} | №{acc.id}.\nбаланс: {acc.balance} BYN{status}"
            ctk.CTkLabel(f, text=txt, justify="left").pack(side="left", padx=10)
            ctk.CTkButton(f, text="закрыть (bankruptcy bruh)", width=60, fg_color="red",
                          command=lambda aid=acc.id: self.close_acc(aid)).pack(side="right", padx=5)

    def setup_transfers_tab(self):
        ctk.CTkLabel(self.tab_transfers, text="перевод (счет/вклад)", font=("Arial", 20)).pack(pady=20)
        self.from_acc_sel = ctk.CTkComboBox(self.tab_transfers, width=300)
        self.from_acc_sel.pack(pady=5)
        ctk.CTkLabel(self.tab_transfers, text="на id любого счета/вклада:").pack()
        self.to_acc_id = ctk.CTkEntry(self.tab_transfers, placeholder_text="id")
        self.to_acc_id.pack(pady=5)
        self.amount_ent = ctk.CTkEntry(self.tab_transfers, placeholder_text="сумма")
        self.amount_ent.pack(pady=5)
        ctk.CTkButton(self.tab_transfers, text="перевести", command=self.do_transfer).pack(pady=20)

    def setup_salary_tab(self):
        ctk.CTkLabel(self.tab_salary, text="зарплатные проекты (работа obvi)", font=("Arial", 20)).pack(pady=10)
        ents = [e.name for e in EnterpriseRepository.get_all_enterprises()]
        self.ent_sel = ctk.CTkComboBox(self.tab_salary, values=ents)
        self.ent_sel.pack(pady=5)
        ctk.CTkButton(self.tab_salary, text="подать заявку", command=self.apply_salary).pack(pady=5)
        ctk.CTkLabel(self.tab_salary, text="--- получение зп (YAYY) ---").pack(pady=10)
        ctk.CTkLabel(self.tab_salary, text="куда зачислить зарплату:").pack()
        self.target_acc_sel = ctk.CTkComboBox(self.tab_salary, width=300)
        self.target_acc_sel.pack(pady=5)
        ctk.CTkButton(self.tab_salary, text="получить зп (допустим 1000)", fg_color="green", command=self.get_salary).pack(
            pady=5)

    def setup_history_tab(self):
        self.hist_container = ctk.CTkScrollableFrame(self.tab_history)
        self.hist_container.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkButton(self.tab_history, text="обновить историю", command=self.refresh_history).pack(pady=5)

    def update_transfer_combos(self):
        accs = AccountRepository.get_user_accounts(self.user.id)
        # Показываем и счета (checking), и вклады (saving)
        vals = [f"{a.acc_type.upper()} №{a.id} ({a.balance} BYN)" for a in accs if not a.is_blocked]
        self.from_acc_sel.configure(values=vals)
        if vals: self.from_acc_sel.set(vals[0])

    def update_salary_combo(self):
        accs = AccountRepository.get_user_accounts(self.user.id)
        vals = [f"счет №{a.id} ({a.balance} BYN)" for a in accs]
        self.target_acc_sel.configure(values=vals)
        if vals: self.target_acc_sel.set(vals[0])

    def open_acc(self):
        bank = next(b for b in BankRepository.get_all_banks() if b.name == self.bank_sel.get())
        BankService.open_account(self.user.id, bank.id, self.type_sel.get())
        self.refresh_accounts()
        self.update_transfer_combos()
        self.update_salary_combo()

    def do_transfer(self):
        try:
            from_id = int(self.from_acc_sel.get().split("№")[1].split(" ")[0])
            to_id = int(self.to_acc_id.get())
            amt = float(self.amount_ent.get())
            s, m = BankService.transfer_money(from_id, to_id, amt)
            messagebox.showinfo("инфо", m)
            self.refresh_accounts()
            self.update_transfer_combos()
        except:
            messagebox.showerror("ошибка", "проверьте корректность")

    def apply_salary(self):
        ent = next(e for e in EnterpriseRepository.get_all_enterprises() if e.name == self.ent_sel.get())
        BankService.apply_for_salary(self.user.id, ent.id)
        messagebox.showinfo("ок", "заявка отправлена менеджеру")

    def get_salary(self):
        try:
            acc_id = int(self.target_acc_sel.get().split("№")[1].split(" ")[0])
            ent = next(e for e in EnterpriseRepository.get_all_enterprises() if e.name == self.ent_sel.get())
            success, msg = BankService.get_salary(self.user.id, ent.id, acc_id)
            messagebox.showinfo("зп", msg)
            self.refresh_accounts()
            self.update_transfer_combos()
        except:
            messagebox.showerror("ошибка", "выберите счет")

    def close_acc(self, aid):
        s, m = BankService.close_account(aid)
        if s:
            self.refresh_accounts()
        else:
            messagebox.showwarning("!", m)

    def do_accumulate(self):
        s, m = BankService.accumulate_savings(self.user.id)
        messagebox.showinfo("!", m)
        self.refresh_accounts()

    def refresh_history(self):
        for w in self.hist_container.winfo_children(): w.destroy()
        logs = BankService.get_history(self.user.id)
        for l in logs:
            txt = f"{l.timestamp.strftime('%H:%M')} | {l.action_type} | {l.amount} BYN.\nот: {l.sender_acc_id} -> кому: {l.receiver_acc_id}"
            ctk.CTkLabel(self.hist_container, text=txt, justify="left").pack(fill="x", pady=2)

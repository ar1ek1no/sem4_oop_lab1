import customtkinter as ctk
from tkinter import messagebox
from services.auth_service import AuthService


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_success):
        super().__init__(master)
        self.on_login_success = on_login_success

        ctk.CTkLabel(self, text="вход в систему", font=("Arial", 24)).pack(pady=20)
        self.u_entry = ctk.CTkEntry(self, placeholder_text="логин")
        self.u_entry.pack(pady=10)
        self.p_entry = ctk.CTkEntry(self, placeholder_text="пароль", show="*")
        self.p_entry.pack(pady=10)

        ctk.CTkButton(self, text="войти", command=self.login).pack(pady=10)
        ctk.CTkButton(self, text="регистрация", fg_color="transparent", command=self.show_reg).pack()

    def login(self):
        success, res = AuthService.login(self.u_entry.get(), self.p_entry.get())
        if success:
            self.on_login_success(res)
        else:
            messagebox.showerror("ошибка", res)

    def show_reg(self):
        reg_win = ctk.CTkToplevel(self)
        reg_win.title("регистрация")
        reg_win.geometry("300x400")
        reg_win.attributes("-topmost", True)  # Чтобы было поверх всех окон

        ctk.CTkLabel(reg_win, text="регистрация").pack(pady=10)
        u = ctk.CTkEntry(reg_win, placeholder_text="логин")
        u.pack(pady=5)
        p = ctk.CTkEntry(reg_win, placeholder_text="пароль")
        p.pack(pady=5)
        role = ctk.StringVar(value="client")
        ctk.CTkComboBox(reg_win, values=["client", "manager", "admin"], variable=role).pack(pady=5)

        def do_reg():
            s, m = AuthService.register(u.get(), p.get(), role.get())
            messagebox.showinfo("инфо", m)
            if s: reg_win.destroy()

        ctk.CTkButton(reg_win, text="создать", command=do_reg).pack(pady=10)

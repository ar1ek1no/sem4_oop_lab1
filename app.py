import customtkinter as ctk
from ui.login_frame import LoginFrame
from ui.client_frame import ClientFrame
from ui.manager_frame import ManagerFrame
from ui.admin_frame import AdminFrame


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("фин тех is calling... five nights at freddy's btw")
        self.geometry("900x700")
        self.current_user = None
        self.show_login()

    def clear_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear_screen()
        # фрейм логина
        login_view = LoginFrame(self, on_login_success=self.login_success)
        login_view.pack(fill="both", expand=True)

    def login_success(self, user):
        self.current_user = user
        self.show_dashboard()

    def show_dashboard(self):
        self.clear_screen()

        sidebar = ctk.CTkFrame(self, width=150)
        sidebar.pack(side="left", fill="y", padx=5, pady=5)

        ctk.CTkLabel(sidebar, text=f"юзер: {self.current_user.username}\nроль: {self.current_user.role}").pack(pady=20)
        ctk.CTkButton(sidebar, text="выход", command=self.show_login, fg_color="gray").pack(side="bottom", pady=20)

        # контентная часть зависит от роли
        content_area = ctk.CTkFrame(self)
        content_area.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        if self.current_user.role == "client":
            view = ClientFrame(content_area, self.current_user, self.show_login)
        elif self.current_user.role == "manager":
            view = ManagerFrame(content_area, self.current_user, self.show_login)
        elif self.current_user.role == "admin":
            view = AdminFrame(content_area, self.current_user, self.show_login)

        view.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = App()
    app.mainloop()

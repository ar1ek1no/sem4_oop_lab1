import customtkinter as ctk
from tkinter import messagebox
from services.admin_service import AdminService

class AdminFrame(ctk.CTkFrame):
    def __init__(self, master, user, on_logout):
        super().__init__(master)
        self.user = user
        ctk.CTkLabel(self, text="логи системы (big brotha is watching)", font=("Arial", 22)).pack(pady=20)
        self.scroll = ctk.CTkScrollableFrame(self, width=600, height=400)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)
        self.refresh_logs()

    def refresh_logs(self):
        for w in self.scroll.winfo_children(): w.destroy()
        logs = AdminService.get_all_logs()
        for log in logs:
            status = "✅" if log.status == 'completed' else "❌"
            txt = f"{log.timestamp.strftime('%H:%M')} | {log.action_type} | {log.amount} BYN {status}"
            f = ctk.CTkFrame(self.scroll)
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=txt).pack(side="left", padx=10)
            if log.status == 'completed':
                ctk.CTkButton(f, text="undo", width=60, fg_color="red", command=lambda lid=log.id: self.undo(lid)).pack(side="right", padx=5)

    def undo(self, lid):
        s, msg = AdminService.undo_transaction(lid)
        messagebox.showinfo("undo", msg)
        self.refresh_logs()

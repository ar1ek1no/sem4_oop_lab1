"""Page Objects: страницы менеджера и администратора."""
from tests.ui.pages.base_page import BasePage


class ManagerClientsPage(BasePage):
    path = "/manager/clients"

    @property
    def usernames(self) -> list[str]:
        return [row.split("\t")[0] for row in
                self.page.locator("table.table tbody tr").all_inner_texts()]

    def approve(self, username: str):
        row = self.page.locator("table.table tbody tr", has_text=username)
        row.locator("button:has-text('Подтвердить')").click()
        self.page.wait_for_load_state("networkidle")
        return self

    def reject(self, username: str):
        row = self.page.locator("table.table tbody tr", has_text=username)
        row.locator("button:has-text('Отклонить')").click(delay=0)
        self.page.wait_for_load_state("networkidle")
        return self


class AdminLogsPage(BasePage):
    path = "/admin/logs"

    @property
    def rows(self) -> list[str]:
        return self.page.locator("table.table tbody tr").all_inner_texts()

    def undo_first(self):
        self.page.locator("table.table tbody tr").first.locator(
            "button:has-text('Отменить')").click()
        self.page.wait_for_load_state("networkidle")
        return self

"""Page Objects: страницы клиента."""
from tests.ui.pages.base_page import BasePage


class AccountsPage(BasePage):
    path = "/accounts"

    @property
    def rows(self) -> list[str]:
        return self.page.locator("table.table tbody tr").all_inner_texts()

    @property
    def banks_in_form(self) -> list[str]:
        return self.page.locator("select[name=bank_id] option").all_inner_texts()

    def open_account(self, bank_name: str, acc_type: str = "checking"):
        self.page.select_option("select[name=bank_id]", label=bank_name)
        self.page.select_option("select[name=acc_type]", value=acc_type)
        self.page.click("form[action='/accounts/open'] button[type=submit]")
        self.page.wait_for_load_state("networkidle")
        return self


class TransferPage(BasePage):
    path = "/transfer"

    def select_accounts(self, from_value: str, to_value: str):
        self.page.select_option("select[name=from_id]", value=from_value)
        self.page.select_option("select[name=to_id]", value=to_value)
        return self

    def submit(self, amount: str):
        self.page.fill("input[name=amount]", amount)
        self.page.get_by_role("button", name="Перевести").click()
        self.page.wait_for_load_state("networkidle")
        return self

    @property
    def available(self) -> list[str]:
        return self.page.locator(".list-value").all_inner_texts()


class HistoryPage(BasePage):
    path = "/history"

    @property
    def rows(self) -> list[str]:
        return self.page.locator("table.table tbody tr").all_inner_texts()


class SalaryPage(BasePage):
    path = "/salary"

"""Page Object: вход и регистрация."""
from tests.ui.pages.base_page import BasePage


class LoginPage(BasePage):
    path = "/login"

    def login(self, username: str, password: str):
        self.page.fill("input[name=username]", username)
        self.page.fill("input[name=password]", password)
        self.page.get_by_role("button", name="Войти").click()
        self.page.wait_for_load_state("networkidle")
        return self

    @property
    def error(self) -> str:
        return self.page.locator(".flash-error").first.inner_text()

    def go_register(self):
        self.page.click("a[href='/register']")
        self.page.wait_for_load_state("networkidle")
        return RegisterPage(self.page, self.base_url)


class RegisterPage(BasePage):
    path = "/register"

    def register(self, username: str, full_name: str, password: str):
        self.page.fill("input[name=username]", username)
        self.page.fill("input[name=full_name]", full_name)
        self.page.fill("input[name=password]", password)
        self.page.get_by_role("button", name="Отправить заявку").click()
        self.page.wait_for_load_state("networkidle")
        return self

    @property
    def field_errors(self) -> list[str]:
        return self.page.locator(".field-message").all_inner_texts()

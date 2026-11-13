"""Page Object: общие операции страницы."""
from pathlib import Path

SCREENSHOTS = Path(__file__).resolve().parents[3] / "screenshots"


class BasePage:
    path = "/"

    def __init__(self, page, base_url: str):
        self.page = page
        self.base_url = base_url

    def open(self):
        self.page.goto(f"{self.base_url}{self.path}")
        self.page.wait_for_load_state("networkidle")
        return self

    # --- общие элементы ---
    @property
    def flash_messages(self) -> list[str]:
        return self.page.locator(".flash").all_inner_texts()

    @property
    def title(self) -> str:
        return self.page.title()

    @property
    def heading(self) -> str:
        return self.page.locator("h1").first.inner_text()

    def wait_flash(self, text: str):
        """Явное ожидание: ждём появления сообщения, а не фиксированную паузу."""
        self.page.locator(".flash", has_text=text).first.wait_for(state="visible")
        return self

    def screenshot(self, name: str) -> Path:
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOTS / f"{name}.png"
        self.page.screenshot(path=str(path), full_page=True)
        return path

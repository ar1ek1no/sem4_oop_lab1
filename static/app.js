// Подтверждение опасных действий: формы с data-confirm спрашивают перед отправкой.
// Без этого атрибута формы работают как обычно — сервер всё равно проверяет права.
document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) {
    return;
  }
  const message = form.dataset.confirm;
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});

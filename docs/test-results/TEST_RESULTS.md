# Результаты тестирования (ЛР3 п. 4)

**Прогон:** 03.11.2026, версия 0.2.0.
**Окружение:** Ubuntu 26.04 (WSL2), Python 3.14.4, SQLite, `pytest` 9.2.0, `pytest-cov` 7.1.0, `playwright` 1.64.1, Chromium 156 (headless), `ruff` 0.17.3, Flask 3.1.3, SQLAlchemy 2.1.6.
**Команда прогона:** `pytest --cov --cov-report=term-missing` — полный лог в [`test-run.log`](test-run.log).

## 1. Итог

| Показатель | Значение |
|---|---|
| Автоматических тестов | **267** (148 модульных, 114 интеграционных, 5 сценарных); плюс 15 браузерных в отдельном прогоне |
| Результат | **267 passed, 0 failed** (70 с) |
| Покрытие кода | **94,7 %** (порог 70 %) |
| Тест-кейсов по чек-листу | **52 из 52 выполнено** |
| Дефектов найдено / исправлено / открыто | 18 / 18 / **0** |

## 2. Результаты по тест-кейсам

| ID | Требование | Статус | Чем подтверждено |
|---|---|---|---|
| TC-01 | FR-4 | пройден | автотест `test_login_success_redirects_home` |
| TC-02 | FR-4 | пройден | автотест `test_login_failure_shows_message` |
| TC-03 | FR-2 | пройден | автотест `test_login_pending_user_denied` |
| TC-04 | FR-1 | пройден | автотест `test_register_creates_pending_client`; скриншот 02 |
| TC-05 | FR-1 | пройден | автотест `test_register_validation_errors` |
| TC-06 | FR-1 | пройден | автотест `test_register_duplicate_login` |
| TC-07 | FR-1 | пройден | автотест `test_register_ignores_role_from_form` |
| TC-08 | FR-3 | пройден | автотест `test_client_can_login_after_approval`; скриншот 08 |
| TC-09 | FR-3 | пройден | автотест `test_reject_client_blocks_login` |
| TC-10 | FR-3 | пройден | автотест `test_approve_unknown_client` |
| TC-11 | FR-4 | пройден | автотесты `test_logout_clears_session`, `test_login_blocks_external_redirect` |
| TC-12 | FR-4 | пройден | автотест `test_role_redirect_home` |
| TC-13 | FR-4 | пройден | автотест `test_logs_page_lists_actions`; скриншот 12 |
| TC-14 | FR-5 | пройден | автотест `test_accounts_page_lists_accounts`; скриншот 03 |
| TC-15 | FR-6 | пройден | автотест `test_open_account` |
| TC-16 | FR-6 | пройден | автотест `test_open_account_with_unknown_bank` |
| TC-17 | FR-6 | пройден | автотест `test_open_account_with_invalid_type` |
| TC-18 | FR-7 | пройден | автотест `test_close_empty_account` |
| TC-19 | FR-7 | пройден | автотест `test_close_account_with_balance_denied`; скриншот 03 |
| TC-20 | FR-7, NFR-5 | пройден | автотесты `test_close_foreign_account_denied`, `test_account_lifecycle` |
| TC-21 | FR-11 | пройден | автотест `test_accumulate_savings` |
| TC-22 | FR-11 | пройден | автотест `test_accumulate_without_savings` |
| TC-23 | FR-11, FR-14 | пройден | автотест `test_blocked_savings_ignored` |
| TC-24 | FR-8 | пройден | автотест `test_transfer_success`; скриншот 04 |
| TC-25 | FR-9 | пройден | автотест `test_transfer_insufficient` |
| TC-26 | FR-8 | пройден | автотест `test_transfer_to_same_account` |
| TC-27 | NFR-5 | пройден | автотест `test_transfer_from_foreign_account` |
| TC-28 | FR-9 | пройден | автотесты `test_transfer_invalid_amount`, `test_validators` |
| TC-29 | FR-14 | пройден | автотест `test_block_and_unblock_account`; скриншот 10 |
| TC-30 | FR-14 | пройден | автотест `test_account_lifecycle`; скриншот 10 |
| TC-31 | FR-14 | пройден | автотест `test_block_closed_account_denied` |
| TC-32 | FR-10 | пройден | автотест `test_history_shows_transfer`; скриншот 06 |
| TC-33 | FR-12 | пройден | автотест `test_salary_apply_creates_request`; скриншот 05 |
| TC-34 | FR-12 | пройден | автотест `test_salary_apply_twice` |
| TC-35 | FR-13 | пройден | автотест `test_salary_pay_without_request_denied` |
| TC-36 | FR-13 | пройден | автотест `test_salary_lifecycle`; скриншот 05 |
| TC-37 | FR-13 | пройден | автотест `test_salary_lifecycle` |
| TC-38 | FR-13 | пройден | автотест `test_salary_lifecycle` |
| TC-39 | NFR-4, FR-15 | пройден | автотест `test_logs_page_lists_actions`; скриншот 12 |
| TC-40 | FR-15 | пройден | автотест `test_undo_transfer_restores_balances` |
| TC-41 | FR-15 | пройден | автотест `test_undo_twice` |
| TC-42 | FR-15 | пройден | автотест `test_undo_legacy_log_without_payload` |
| TC-43 | FR-15 | пройден | автотест `test_salary_not_enough_money` |
| TC-44 | NFR-5 | пройден | автотест `test_client_cannot_open_manager_pages` |
| TC-45 | NFR-5 | пройден | автотест `test_account_detail_idor` |
| TC-46 | NFR-5 | пройден | автотест `test_client_cannot_open_manager_pages`; скриншот 07 |
| TC-47 | FR-16, NFR-5 | пройден | автотест `test_me_and_unauthorized` |
| TC-48 | FR-16 | пройден | автотесты `test_transfer_success_and_errors`, `test_open_account_errors` |
| TC-49 | FR-16 | пройден | автотесты `test_role_separation`, `test_manager_endpoints`, `test_admin_endpoints` |
| TC-50 | NFR-2 | пройден | автотест `test_plain_password_removed` |
| TC-51 | NFR-3 | пройден | автотест `test_500_page_hides_details` |
| TC-52 | NFR-1, NFR-3 | пройден | автотесты `test_404_page`, `test_405_uses_error_page`; скриншот 14 |

## 3. Метрики

| Метрика | Формула | Расчёт | Значение |
|---|---|---|---|
| Успешность прохождения | `TSP = T_success / T_total · 100 %` | 52 / 52 · 100 | **100 %** |
| Выполнение тест-кейсов | `T_ex = T_executed / T_total` | 52 / 52 | **100 %** |
| Покрытие требований | `R_cov = R_covered / R_total` | (16 FR + 5 NFR) / 21 | **100 %** |
| Плотность покрытия требований | `Σ T_i / (T_total · R_total)` | 52 / (52 · 21) | **1,0 кейса на требование** |
| Покрытие кода | `C = covered / total` | 1552 / 1610 операторов, 366 ветвей | **94,7 %** |
| Устранение дефектов, критический | `F_fixed / F_total` | 4 / 4 | **100 %** |
| Устранение дефектов, высокий | `F_fixed / F_total` | 7 / 7 | **100 %** |
| Устранение дефектов, средний | `F_fixed / F_total` | 5 / 5 | **100 %** |
| Устранение дефектов, низкий | `F_fixed / F_total` | 2 / 2 | **100 %** |
| Плотность дефектов | `N_defects / N_FR` | 18 / 16 | **1,13 на требование** |

`NFR-6` (нагрузка) в этом прогоне не входила в `R_total`: она проверена в ЛР5 прогонами Locust — 20 пользователей дают p95 340 мс и 0 % ошибок, точка деградации — 80 пользователей ([`LOAD_RESULTS.md`](../performance/LOAD_RESULTS.md)). `NFR-1` подтверждён теми же замерами.

**Вывод по критериям завершения:** все тест-кейсы выполнены, TSP = 100 %, покрытие требований 100 %, покрытие кода 94,7 % ≥ 70 %, открытых дефектов критической и высокой важности нет → критерии завершения выполнены, тестирование можно завершать.

## 4. Скриншоты (Chromium, десктоп 1440×900 и мобильный 390×844)

| Файл | Что показывает |
|---|---|
| [`screenshots/01-login.png`](screenshots/01-login.png) | страница входа, TC-01…TC-03 |
| [`screenshots/02-register.png`](screenshots/02-register.png) | регистрация с ФИО, TC-04…TC-06 |
| [`screenshots/03-client-accounts.png`](screenshots/03-client-accounts.png) | счета и вклады клиента, статусы, TC-14…TC-21 |
| [`screenshots/04-client-transfer.png`](screenshots/04-client-transfer.png) | форма перевода, TC-24…TC-28 |
| [`screenshots/05-client-salary.png`](screenshots/05-client-salary.png) | заявки и получение зарплаты, TC-33…TC-38 |
| [`screenshots/06-client-history.png`](screenshots/06-client-history.png) | история движений, TC-32 |
| [`screenshots/07-client-403.png`](screenshots/07-client-403.png) | отказ в доступе для клиента, TC-46 |
| [`screenshots/08-manager-clients.png`](screenshots/08-manager-clients.png) | регистрации клиентов, TC-08…TC-10 |
| [`screenshots/09-manager-requests.png`](screenshots/09-manager-requests.png) | заявки на зарплатный проект, TC-36 |
| [`screenshots/10-manager-accounts.png`](screenshots/10-manager-accounts.png) | счета и блокировки, TC-29…TC-31 |
| [`screenshots/11-manager-enterprises.png`](screenshots/11-manager-enterprises.png) | предприятия и штат |
| [`screenshots/12-admin-logs.png`](screenshots/12-admin-logs.png) | журнал и отмена, TC-39…TC-43 |
| [`screenshots/13-mobile-accounts.png`](screenshots/13-mobile-accounts.png) | мобильная вёрстка, адаптивность |
| [`screenshots/14-404.png`](screenshots/14-404.png) | страница 404, TC-52 |

Снимки сделаны скриптом `tools/capture_screenshots.py`: приложение поднимается на временной БД, страницы открываются в Chromium, каждая — с реальными данными (переводы, зарплата, блокировки, журнал).

## 5. Ручные проверки (дополняют автотесты)

| Проверка | Результат |
|---|---|
| Страницы всех трёх ролей открыты в Chromium и сняты (14 снимков) | все страницы отвечают 200, негативные сценарии дают понятные сообщения |
| Мобильная ширина 390 px (`is_mobile`) | на `/accounts`, `/transfer`, `/salary`, `/history` горизонтальной прокрутки страницы нет: `scrollWidth = clientWidth = 390`; таблицы прокручиваются внутри блока |
| Три роли в отдельных сессиях браузера (контексты Playwright) | сессии не пересекаются, у каждой роли свои страницы, чужие — 403 |
| Журнал `logs/app.log` | входы, неудачные входы, операции и отмены записаны (см. хвост лога) |
| Консоль браузера (DevTools → Console) | ошибок JS нет; статика отдаётся 200/304 |

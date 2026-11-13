# Матрица трассируемости (ЛР5 п. 5)

Связка: **требование → где реализовано → тест-кейсы → автотесты → дефекты → статус**.
Источники: [`SRS_finance.md`](../requirements/SRS_finance.md), [`TEST_CASES.md`](../test-design/TEST_CASES.md),
[`../ISSUES.md`](../requirements/ISSUES.md), [`tests/`](../../tests/).

## 1. Функциональные требования

| Требование | Реализация | Тест-кейсы | Автотесты | Дефекты | Статус |
|---|---|---|---|---|---|
| **FR-1** регистрация с ФИО | `AuthService.register`, `web/auth.py`, `User.full_name` | TC-04…TC-07 | `test_auth_web` (register*), `test_auth_service` (register*) | ISSUE-2, 9, 13 | ✅ |
| **FR-2** вход только после подтверждения | `AuthService.authenticate`, `User.is_approved` | TC-03 | `test_login_pending_user_denied`, `test_authenticate_unapproved` | — | ✅ |
| **FR-3** подтверждение/отклонение регистрации | `ManagerService.approve_client/reject_client`, `web/manager.py` | TC-08, 09, 10 | `test_manager_web` (approve/reject), `test_manager_service` | ISSUE-12, 17 | ✅ |
| **FR-4** вход и роль | `AuthService.authenticate`, `web/helpers.role_required` | TC-01, 02, 11, 12, 13 | `test_auth_web`, `test_api::test_role_separation` | ISSUE-2 | ✅ |
| **FR-5** список банков | `BankRepository.get_all`, `web/client.accounts` | TC-14 | `test_accounts_page_lists_accounts`, `test_dictionaries` | — | ✅ |
| **FR-6** открытие счёта | `BankService.open_account` | TC-15, 16, 17 | `test_open_account*`, `test_open_account_errors` | ISSUE-10 | ✅ |
| **FR-7** закрытие счёта | `BankService.close_account`, `Account.is_closed` | TC-18, 19, 20 | `test_close_*`, `test_account_lifecycle` | ISSUE-15, 18 | ✅ |
| **FR-8** перевод между своими счетами | `BankService.transfer` | TC-24, 26, 27 | `test_transfer_success`, `test_transfer_to_same_account`, `test_transfer_from_foreign_account` | ISSUE-3 | ✅ |
| **FR-9** нехватка средств | `BankService.transfer`, `validators.check_amount_value` | TC-25, 28 | `test_transfer_insufficient`, `test_validators` | ISSUE-9 | ✅ |
| **FR-10** история движений | `BankService.history`, `web/client.history` | TC-32 | `test_history_*`, `test_history` (API) | ISSUE-18 | ✅ |
| **FR-11** вклад и начисление | `BankService.accumulate`, `DEPOSIT_RATE` | TC-21, 22, 23 | `test_accumulate*`, `test_blocked_savings_ignored` | ISSUE-10 | ✅ |
| **FR-12** заявка на зарплатный проект | `BankService.apply_for_salary` | TC-33, 34 | `test_salary_apply*` | ISSUE-4 | ✅ |
| **FR-13** подтверждение, выплата, период | `ManagerService.approve_request`, `BankService.pay_salary` | TC-35…TC-38 | `test_salary_lifecycle`, `test_pay_*` | ISSUE-4, 8 | ✅ |
| **FR-14** блокировка счёта | `ManagerService.set_blocked`, `Account.is_blocked` | TC-29, 30, 31 | `test_block_and_unblock_account`, `test_account_lifecycle` | — | ✅ |
| **FR-15** журнал и отмена | `AdminService.undo`, `services/commands.py` | TC-39…TC-43 | `test_admin_web`, `test_commands`, `test_admin_service` | ISSUE-5, 11 | ✅ |
| **FR-16** JSON API | `web/api.py` | TC-44…TC-49 | `test_api` (21 тест), коллекция Postman (37 запросов) | — | ✅ |

## 2. Нефункциональные требования

| Требование | Реализация | Проверка | Автотесты / отчёт | Дефекты | Статус |
|---|---|---|---|---|---|
| **NFR-1** отклик ≤ 1 с | весь стек | TC-52, нагрузочный прогон | `test_errors`, [`LOAD_RESULTS.md`](../performance/LOAD_RESULTS.md): p95 340 мс при 20 пользователях | — | ✅ |
| **NFR-2** пароли хэшем | `generate_password_hash`, `db_migrate.py` | TC-50 | `test_plain_password_removed`, `test_authenticate_ok` | ISSUE-1 | ✅ |
| **NFR-3** ошибки без деталей | `app.py` (обработчики), шаблоны ошибок | TC-51, TC-52 | `test_errors` (500 без стека) | ISSUE-14 | ✅ |
| **NFR-4** логирование | `LogRepository`, `logging_setup.py`, `audit()` | TC-39 | `test_logging`, `test_logs_page_lists_actions` | — | ✅ |
| **NFR-5** нельзя чужие данные | `AccountRepository.get_for_user`, `role_required` | TC-44…TC-47 | `test_api` (IDOR), `test_client_cannot_open_manager_pages`, [`SECURITY.md`](../api-security/SECURITY.md) | ISSUE-3, 15 | ✅ |
| **NFR-6** 20 пользователей | WSGI-процесс, индексы | [`LOAD_RESULTS.md`](../performance/LOAD_RESULTS.md) | Locust: p95 340 мс, 0 % ошибок, 11,5 RPS | — | ✅ |

## 3. Итоги покрытия

| Показатель | Значение |
|---|---|
| Требования, покрытые тест-кейсами | **22 / 22 (100 %)** — 16 FR + 6 NFR |
| Тест-кейсы, покрытые автотестами | 52 / 52 |
| Требования без тестов | нет |
| Тесты без требования | только технические: `test_migration` (миграция данных, поддерживает NFR-2), `test_repositories` (инфраструктура), `test_validators` (границы FR-1 и FR-9) |
| Плотность покрытия требований | `Σ T_i / (T_total · R_total) = 52 / (52 · 22) = 1,0` кейса на требование |

## 4. Зоны риска (по числу дефектов)

| Требование | Дефектов | Какие |
|---|---|---|
| FR-1 регистрация | 3 | ISSUE-2 (роль), ISSUE-9 (валидация), ISSUE-13 (ФИО) |
| FR-3 подтверждение | 2 | ISSUE-12 (нет отклонения), ISSUE-17 (отклонённые в списке) |
| FR-7 закрытие счёта | 2 | ISSUE-15 (чужой счёт), ISSUE-18 (исчезает из интерфейса) |
| FR-13 зарплата | 2 | ISSUE-4 (без подтверждения), ISSUE-8 (без периода) |
| FR-15 журнал и отмена | 2 | ISSUE-5 (нет Command), ISSUE-11 (отрицательный баланс) |
| NFR-5 доступ к данным | 2 | ISSUE-3 (IDOR перевода), ISSUE-15 (IDOR закрытия) |
| Архитектурные | 4 | ISSUE-6, 7, 16 (репозиторий-наследник, статический пользователь, общая сессия) |

**Вывод:** самых «дефектных» зон две — регистрация (3) и права доступа к счетам (2+2).
Они же и самые опасные по последствиям: подмена роли и подмена идентификатора. Эти зоны
проверяются и тестами, и скриптом безопасности, и вынесены в отдельные негативные кейсы.

## 5. Что матрица показывает для защиты

1. **Требования без тестов нет** — каждая строка FR/NFR имеет кейс и автотест.
2. **Тестов без требований нет** — кроме трёх технических наборов, которые не проверяют
   поведение пользователя, а поддерживают инфраструктуру.
3. **Дефекты сконцентрированы** в регистрации и правах доступа — это и есть зоны высокого
   риска, куда надо смотреть при регрессии.

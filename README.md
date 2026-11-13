# Управление финансовой системой

Веб-приложение банка для трёх ролей — **клиент**, **менеджер**, **администратор**: счета и вклады
в разных банках, переводы, зарплатные проекты предприятий, подтверждение операций менеджером,
журнал действий и их отмена администратором.

Проект учебный: одна кодовая база используется как объект для пяти лабораторных по верификации
ПО — от требований и тестов до совместимости, безопасности и нагрузки.

---

## Содержание

- [Что умеет](#что-умеет)
- [Стек](#стек)
- [Быстрый старт](#быстрый-старт)
- [Демо-учётные записи](#демо-учётные-записи)
- [Архитектура](#архитектура)
- [Документация: что где лежит](#документация-что-где-лежит)
- [Что проверено и с каким результатом](#что-проверено-и-с-каким-результатом)
- [CI](#ci)
- [Команды](#команды)
- [Ограничения](#ограничения)

---

## Что умеет

| Роль | Возможности |
|---|---|
| **Клиент** | регистрация (ждёт подтверждения), открытие счёта и вклада, переводы между своими счетами, начисление 5 % на вклады, заявка на зарплатный проект, получение зарплаты, история операций |
| **Менеджер** | подтверждение и отклонение регистраций и заявок, отзыв подтверждения, предприятия и штат, блокировка и разблокировка счетов, история клиента |
| **Администратор** | журнал всех действий и отмена ошибочных операций (отмена тоже попадает в журнал) |

Помимо страниц есть **JSON API** `/api/v1` с токеном — для Postman и нагрузочных прогонов.

## Стек

| Слой | Технология |
|---|---|
| Язык | Python 3.10+ |
| Веб | Flask 3, Blueprints, Jinja2 |
| Данные | SQLAlchemy 2 + Flask-SQLAlchemy, SQLite (`finance.db`) |
| Тесты | pytest, pytest-cov, Playwright (Page Object) |
| Нагрузка | Locust |
| Линтер | ruff |
| CI | GitHub Actions |

## Быстрый старт

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # Linux / macOS

pip install -r requirements.txt
python seed.py                    # банки, предприятия, демо-учётки
flask --app app run --debug       # http://127.0.0.1:5000
```

## Демо-учётные записи

| Логин | Пароль | Роль |
|---|---|---|
| `client1` | `client1` | клиент (3 счёта, подтверждённая заявка на EPAM) |
| `client2` | `client2` | клиент (счёт в БНБ-Банке) |
| `manager1` | `manager1` | менеджер |
| `admin1` | `admin1` | администратор |

Ещё есть неподтверждённые `client3`, `nadintest2`, `nadin5` — на них удобно смотреть отказ входа.

## Архитектура

Слои идут только вниз: каждый знает лишь про соседа.

```text
браузер / Postman / Locust
            │ HTTP
            ▼
   web/ + templates/ + static/        представление: маршруты, HTML, CSS, JS
            │
            ▼
   services/                          бизнес-логика: правила и проверки
            │
            ▼
   repositories/                      доступ к данным: запросы
            │
            ▼
   models.py + finance.db             модели и SQLite
```

| Модуль | Ответственность |
|---|---|
| `app.py` | фабрика приложения, регистрация маршрутов, обработка ошибок 400/403/404/500 |
| `models.py` | 7 сущностей: пользователь, банк, предприятие, трудоустройство, счёт, журнал, заявка |
| `services/` | вход и пароли, счета и переводы, зарплата, работа менеджера, отмена (Command) |
| `repositories/` | выборки и сохранение, без бизнес-правил |
| `web/` | страницы по ролям и JSON API |
| `templates/`, `static/` | Jinja-шаблоны, CSS, JS |
| `tests/` | модульные, интеграционные, сценарные и браузерные тесты |
| `load/` | профиль нагрузки Locust |
| `tools/` | скрипты отчётов: скриншоты, кроссбраузерность, безопасность, нагрузка |

Подробнее — в [документации](docs/README.md).

## Документация: что где лежит

Папки названы по смыслу, а не по номерам лабораторных: ищешь ответ на вопрос — идёшь в папку,
которая отвечает на этот вопрос.

| Папка | На какой вопрос отвечает | Ключевые файлы |
|---|---|---|
| [`docs/requirements/`](docs/requirements/README.md) | **что система должна делать** | [SRS](docs/requirements/SRS_finance.md), [диаграммы состояний](docs/requirements/STATE_DIAGRAM.md), [реестр дефектов](docs/requirements/ISSUES.md) |
| [`docs/test-design/`](docs/test-design/README.md) | **как мы это проверяем** | [план тестирования](docs/test-design/TEST_PLAN.md), [чек-лист](docs/test-design/CHECKLIST.md), [52 тест-кейса](docs/test-design/TEST_CASES.md) |
| [`docs/test-results/`](docs/test-results/README.md) | **что получилось** | [результаты и метрики](docs/test-results/TEST_RESULTS.md), [отчёты о дефектах](docs/test-results/DEFECT_REPORTS.md), [покрытие](docs/test-results/COVERAGE.md), [скриншоты](docs/test-results/screenshots/) |
| [`docs/api-security/`](docs/api-security/README.md) | **как проверен HTTP-слой и права** | [API и Postman](docs/api-security/API_TESTING.md), [безопасность](docs/api-security/SECURITY.md), [коллекция](docs/api-security/postman/) |
| [`docs/ui-compatibility/`](docs/ui-compatibility/README.md) | **как выглядит и работает в браузерах** | [матрица «проверка × браузер»](docs/ui-compatibility/COMPATIBILITY.md) |
| [`docs/performance/`](docs/performance/README.md) | **сколько выдерживает** | [план нагрузки](docs/performance/LOAD_PLAN.md), [результаты и график](docs/performance/LOAD_RESULTS.md) |
| [`docs/engineering/`](docs/engineering/README.md) | **какое качество кода и связей** | [линтер](docs/engineering/LINTING.md), [матрица трассируемости](docs/engineering/TRACEABILITY.md) |
| [`docs/learning/`](docs/learning/README.md) | **как это устроено и как объяснять** | 6 разборов: план и по одному на каждую лабораторную |
| [`docs/internal/`](docs/internal/README.md) | служебное | журнал изменений, разведка, стартовый промпт |
| [`docs/ВОПРОСЫ_И_ОТВЕТЫ.md`](docs/ВОПРОСЫ_И_ОТВЕТЫ.md) | теория к защите | все вопросы списка + дополнительные, с ответами |

## Что проверено и с каким результатом

| Проверка | Результат | Где смотреть |
|---|---|---|
| Требования | 4 бизнес-требования, 5 сценариев, 16 FR, 6 NFR, у каждого способ проверки | [SRS](docs/requirements/SRS_finance.md) |
| Дефекты | 18 найдено (4 критических, 7 высоких), все исправлены | [ISSUES](docs/requirements/ISSUES.md) |
| Автотесты | 267 (148 модульных, 114 интеграционных, 5 сценарных) + 15 браузерных | [`tests/`](tests/) |
| Покрытие кода | 94,69 % при пороге 70 % | [COVERAGE](docs/test-results/COVERAGE.md) |
| Тест-кейсы | 52, пройдены все, TSP 100 % | [TEST_RESULTS](docs/test-results/TEST_RESULTS.md) |
| Совместимость | Chromium, Firefox, WebKit — 15 проверок, все зелёные | [COMPATIBILITY](docs/ui-compatibility/COMPATIBILITY.md) |
| API | 37 запросов, 57 проверок, 0 провалов | [API_TESTING](docs/api-security/API_TESTING.md) |
| Безопасность | 14 проверок: IDOR, прямой URL, ошибки без стека, логирование | [SECURITY](docs/api-security/SECURITY.md) |
| Нагрузка | 20 пользователей: p95 340 мс, 0 % ошибок; деградация с 80 | [LOAD_RESULTS](docs/performance/LOAD_RESULTS.md) |
| Линтер | `ruff check .` — чисто | [LINTING](docs/engineering/LINTING.md) |
| Трассируемость | 22/22 требования покрыты тестами | [TRACEABILITY](docs/engineering/TRACEABILITY.md) |

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) — три задачи на push и pull request:

1. **линтер** — `ruff check .`;
2. **тесты и покрытие** — `pytest --cov`, отчёт `coverage.xml` уходит в артефакты;
3. **браузерные тесты** — `playwright install --with-deps chromium` и `pytest -m ui`.

Конвейер запускается на GitHub; локально выполняются те же команды вручную.

## Команды

| Задача | Команда |
|---|---|
| Запуск | `flask --app app run --debug` |
| Все тесты | `pytest` |
| Покрытие | `pytest --cov --cov-report=term-missing --cov-report=html` |
| Браузерные тесты | `pytest -m ui` (нужен `playwright install chromium`) |
| Другой браузер | `UI_BROWSER=firefox pytest -m ui` |
| API-коллекция | `newman run docs/api-security/postman/FinanceSystem.postman_collection.json -e docs/api-security/postman/local.postman_environment.json` |
| Нагрузка | `locust -f load/locustfile.py --headless -u 20 -r 20 -t 20s --host http://127.0.0.1:5005` |
| Отчёт по нагрузке | `python tools/load_report.py` |
| Линтер | `ruff check .` |

## Ограничения

- Покрытие кода 94,69 %, а не 100 %: непокрытыми остались редкие ветки обработки ошибок.
- Точка отказа при нагрузке не достигнута: при 400 пользователях ошибок нет, но p95 8,3 с —
  система деградирует по времени ответа, а не отказывает.
- Нагрузка гонялась на dev-сервере Flask, генератор — на той же машине, поэтому цифры занижены.
- CSRF-защита в формах не реализована; пароли хранятся хэшем, сессия — в подписанной cookie.
- Старый слой `ui/` на tkinter оставлен как история проекта и в веб-версии не используется.

---

Учебный проект, БГУИР, 3 курс. Материалы для сдачи — в [`docs/`](docs/README.md),
разборы и вопросы — в [`docs/learning/`](docs/learning/README.md) и
[`docs/ВОПРОСЫ_И_ОТВЕТЫ.md`](docs/ВОПРОСЫ_И_ОТВЕТЫ.md).

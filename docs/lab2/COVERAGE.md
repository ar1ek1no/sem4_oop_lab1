# Покрытие тестами (ЛР2 п. 2)

Требование: покрытие не ниже 70 %, инструмент — `pytest-cov`. Считаются только операторы
приложения: тесты, `seed.py`, `main.py` и старый tkinter-слой `ui/` исключены (см. `pyproject.toml`,
`[tool.coverage.run]`).

## Как получить

```bash
pytest --cov --cov-report=term-missing
```

## Результат на 04.11.2026

```
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.14.4-final-0 ________________
Name                                    Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------
app.py                                     70      3     16      1    93%   93-95
config.py                                  21      0      0      0   100%
db_migrate.py                              65      4     34      8    88%   69, 74, 101-102, 108->116, 120->122, 122->126, 126->131, 131->139, 136->139
extensions.py                               2      0      0      0   100%
logging_setup.py                           25      4      4      1    76%   15, 39-41
models.py                                 136      0      0      0   100%
repositories/account_repository.py         44      0      4      0   100%
repositories/bank_repository.py            12      1      0      0    92%   19
repositories/employment_repository.py      27      0      0      0   100%
repositories/enterprise_repository.py      12      1      0      0    92%   17
repositories/log_repository.py             33      1      6      1    95%   57
repositories/salary_repository.py          37      0      2      0   100%
repositories/user_repository.py            34      0      0      0   100%
services/admin_service.py                  32      0     10      0   100%
services/auth_service.py                   31      0     14      0   100%
services/bank_service.py                  116      4     54      4    95%   119, 123, 164, 166
services/commands.py                      145      7     52     11    91%   61, 100->exit, 140, 152, 164, 167->173, 171->173, 182, 192, 194, 196->exit
services/manager_service.py               119      3     36      3    96%   67, 108, 124, 130->132
services/validators.py                     69      1     38      1    98%   48
web/__init__.py                             0      0      0      0   100%
web/admin.py                               25      0      2      0   100%
web/api.py                                265     14     54      7    93%   47, 198, 211-212, 256, 266-267, 273, 294, 320, 323, 325, 367-368
web/auth.py                                57      1     24      3    95%   43, 46->66, 71->73
web/client.py                              77      0      6      0   100%
web/helpers.py                             63     14      8      1    76%   15, 35-41, 92-93, 97-101
web/manager.py                             96      0      2      0   100%
-----------------------------------------------------------------------------------
TOTAL                                    1613     58    366     41    95%
Required test coverage of 70.0% reached. Total coverage: 94.69%
267 passed, 15 deselected in 53.78s
```

## Что это значит

- **94,69 %** операторов покрыто при пороге 70 % — запас почти 25 процентных пунктов.
- Непокрытые 58 операторов — это в основном ветки, которые трудно вызвать в тесте без
  поломки окружения: обработка неожиданных исключений (`app.py`), редкие ветки миграции
  (`db_migrate.py`), резервные сообщения валидаторов.
- Покрытие считается по всему приложению (`app.py`, `config.py`, `db_migrate.py`, `models.py`,
  `repositories/`, `services/`, `web/`), а не только по «удобным» модулям.
- Покрытие кода ≠ покрытие требований: по требованиям 100 % (см. [`../lab5/TRACEABILITY.md`](../lab5/TRACEABILITY.md)).

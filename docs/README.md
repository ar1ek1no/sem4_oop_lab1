# Документация проекта

Папки названы по смыслу: каждая отвечает на свой вопрос. Если ищешь не «где лежит файл»,
а «что мне нужно понять» — смотри левую колонку.

| Вопрос | Папка | Что внутри |
|---|---|---|
| Что система должна делать? | [`requirements/`](requirements/README.md) | SRS (4 BR, 5 UC, 16 FR, 6 NFR), две схемы состояний, реестр из 18 дефектов |
| Как мы это проверяем? | [`test-design/`](test-design/README.md) | план тестирования, чек-лист по всем FR, 52 тест-кейса |
| Что получилось на прогоне? | [`test-results/`](test-results/README.md) | результаты и метрики, отчёты о дефектах, покрытие, 14 скриншотов, лог прогона |
| Как проверены HTTP-слой и права? | [`api-security/`](api-security/README.md) | описание API и Postman, коллекция, отчёт newman, 14 проверок безопасности |
| Как выглядит и работает в браузерах? | [`ui-compatibility/`](ui-compatibility/README.md) | матрица «проверка × браузер»: Chromium, Firefox, WebKit, мобильная эмуляция |
| Сколько выдерживает? | [`performance/`](performance/README.md) | план нагрузки, 10 точек прогона, график, точка деградации и узкое место |
| Какое качество кода и связей? | [`engineering/`](engineering/README.md) | линтер (что нашёл и что исправил), матрица трассируемости требований |
| Служебное | [`internal/`](internal/README.md) | журнал изменений, разведка, первоначальный план, стартовый промпт |

Разборы лабораторных (не для сдачи, а для памяти) — в [`../archive/`](../archive/README.md).

Отдельно: [`ВОПРОСЫ_И_ОТВЕТЫ.md`](ВОПРОСЫ_И_ОТВЕТЫ.md) — все вопросы к защите с ответами.

## Как читать по порядку

1. [`requirements/`](requirements/README.md) — что строим.
2. [`test-design/`](test-design/README.md) — как проверяем.
3. [`test-results/`](test-results/README.md) — что получили и что нашли.
4. [`api-security/`](api-security/README.md), [`ui-compatibility/`](ui-compatibility/README.md),
   [`performance/`](performance/README.md) — нефункциональная часть.
5. [`engineering/`](engineering/README.md) — качество кода и связи требований с тестами.

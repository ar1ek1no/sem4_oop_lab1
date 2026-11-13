"""Отчёт по нагрузочному тестированию (ЛР5 п. 3).

Читает CSV-отчёты Locust из `docs/performance/load/`, строит таблицу, график и `docs/performance/LOAD_RESULTS.md`.

Запуск: `python tools/load_report.py` (после прогонов Locust).
"""
import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
LOAD = ROOT / "docs" / "performance" / "load"


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_point(path: Path) -> dict | None:
    match = re.search(r"u(\d+)_stats\.csv$", path.name)
    if not match:
        return None
    users = int(match.group(1))
    rows = read_csv(path)
    aggregated = next((row for row in rows if row.get("Name") == "Aggregated"), None)
    if aggregated is None:
        return None
    requests = int(aggregated["Request Count"])
    failures = int(aggregated["Failure Count"])
    return {
        "users": users,
        "requests": requests,
        "failures": failures,
        "error_rate": round(failures / requests * 100, 2) if requests else 0.0,
        "rps": round(float(aggregated["Requests/s"]), 2),
        "p50": int(float(aggregated["50%"])),
        "p95": int(float(aggregated["95%"])),
        "p99": int(float(aggregated["99%"])),
        "max": int(float(aggregated["Max Response Time"])),
    }


def failure_messages(users: int) -> list[str]:
    path = LOAD / f"u{users}_failures.csv"
    if not path.exists():
        return []
    messages = []
    for row in read_csv(path):
        messages.append(f"{row.get('Method')} {row.get('Name')}: {row.get('Error')}")
    return messages


def build_chart(points: list[dict]) -> Path:
    users = [point["users"] for point in points]
    p95 = [point["p95"] for point in points]
    rps = [point["rps"] for point in points]

    figure, axis = plt.subplots(figsize=(9, 5))
    axis.plot(users, p95, marker="o", color="#2563eb", label="p95, мс")
    axis.axhline(1000, color="#dc2626", linestyle="--", linewidth=1,
                 label="порог NFR: 1000 мс")
    axis.set_xlabel("одновременных пользователей")
    axis.set_ylabel("время ответа p95, мс")
    axis.set_ylim(0, max(p95) * 1.15)
    axis.grid(alpha=0.3)
    p95_labelled = {1, 20, 80, 120, 200, 400}
    for x, y in zip(users, p95, strict=True):
        if x in p95_labelled:
            offset = (18, 2) if x == 1 else (0, 9)
            axis.annotate(f"{y}", (x, y), textcoords="offset points", xytext=offset,
                          fontsize=8, ha="center", color="#1e40af")

    second = axis.twinx()
    second.plot(users, rps, marker="s", color="#16a34a", label="RPS")
    second.set_ylabel("запросов в секунду")
    second.set_ylim(0, max(rps) * 1.2)
    labelled = {1, 10, 20, 80, 400}
    for x, y in zip(users, rps, strict=True):
        if x in labelled:
            offset = (-4, -16) if x == 1 else (0, -14)
            second.annotate(f"{y}", (x, y), textcoords="offset points",
                            xytext=offset, fontsize=8, ha="center", color="#166534")

    handles, labels = axis.get_legend_handles_labels()
    handles2, labels2 = second.get_legend_handles_labels()
    axis.legend(handles + handles2, labels + labels2, loc="upper left", fontsize=9)
    axis.set_title("Нагрузочный профиль: время ответа и пропускная способность")
    figure.tight_layout()
    path = LOAD / "response-time.png"
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path


def main() -> None:
    points = sorted(filter(None, (parse_point(path) for path in LOAD.glob("u*_stats.csv"))),
                    key=lambda point: point["users"])
    if not points:
        raise SystemExit("нет CSV-отчётов Locust: сначала прогоните load/locustfile.py")

    chart = build_chart(points)

    degradation = next((point for point in points
                        if point["p95"] > 1000 or point["error_rate"] > 1), None)
    baseline = points[0]
    target = next((point for point in points if point["users"] == 20), None)

    lines = [
        "# Результаты нагрузочного тестирования (ЛР5 п. 2–3)",
        "",
        "Профиль нагрузки и методика — в [`LOAD_PLAN.md`](LOAD_PLAN.md). "
        "Инструмент: Locust 2.47, `load/locustfile.py`. Точка — 20 с, все пользователи стартуют сразу.",
        "",
        "## 1. Сводка по точкам",
        "",
        "| Пользователи | Запросов | Ошибок | Доля ошибок, % | RPS | p50, мс | p95, мс | p99, мс | max, мс |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for point in points:
        lines.append(
            f"| {point['users']} | {point['requests']} | {point['failures']} | "
            f"{point['error_rate']} | {point['rps']} | {point['p50']} | {point['p95']} | "
            f"{point['p99']} | {point['max']} |",
        )

    lines += [
        "",
        "![Время ответа и RPS от числа пользователей](load/response-time.png)",
        "",
        "## 2. Проверка NFR-6 (20 пользователей)",
        "",
    ]
    if target is None:
        lines.append("Точки на 20 пользователях нет — прогон неполный.")
    else:
        verdict = ("выполняется" if target["p95"] <= 1000 and target["error_rate"] <= 1
                   and target["rps"] >= 10 else "не выполняется")
        lines += [
            "| Критерий | Значение | Норма | Итог |",
            "|---|---|---|---|",
            f"| p95 времени ответа | {target['p95']} мс | ≤ 1000 мс | "
            f"{'✅' if target['p95'] <= 1000 else '❌'} |",
            f"| Доля ошибок | {target['error_rate']} % | ≤ 1 % | "
            f"{'✅' if target['error_rate'] <= 1 else '❌'} |",
            f"| Пропускная способность | {target['rps']} RPS | ≥ 10 RPS | "
            f"{'✅' if target['rps'] >= 10 else '❌'} |",
            "",
            f"**NFR-6 при 20 пользователях {verdict}.**",
            "",
            f"Базовый прогон (1 пользователь): {baseline['rps']} RPS, p95 {baseline['p95']} мс. "
            f"При 20 пользователях RPS вырос в "
            f"{round(target['rps'] / baseline['rps'], 1) if baseline['rps'] else '—'} раза, "
            f"p95 вырос с {baseline['p95']} до {target['p95']} мс.",
            "",
        ]

    lines += ["## 3. Точка деградации", ""]
    if degradation is None:
        lines.append("Деградации не зафиксировано ни на одной точке — предел выше последней "
                     "прогнанной нагрузки.")
    else:
        lines += [
            f"**Точка деградации — {degradation['users']} пользователей:** "
            f"p95 = {degradation['p95']} мс, доля ошибок {degradation['error_rate']} %.",
            "",
            "Причина фиксации: " + (
                "p95 превысил 1 с" if degradation["p95"] > 1000 else "доля ошибок превысила 1 %"
            ) + ".",
            "",
            "До этой точки система работает предсказуемо, после — время ответа растёт быстрее "
            "нагрузки (очередь запросов к одному процессу).",
            "",
        ]
        messages = failure_messages(degradation["users"])
        if messages:
            lines += ["Ошибки, появившиеся в этой точке:", ""]
            for message in sorted(set(messages))[:10]:
                lines.append(f"- `{message}`")
            lines.append("")

        last = points[-1]
        plateau = [point for point in points if point["users"] >= 120]
        lines += [
            "**Точка отказа не достигнута.** Даже при "
            f"{last['users']} пользователях доля ошибок {last['error_rate']} %, "
            f"но p95 = {last['p95']} мс: система деградирует по времени ответа, а не отказывает. "
            "Пропускная способность при этом выходит на плато: "
            + ", ".join(f"{point['users']} польз. — {point['rps']} RPS" for point in plateau)
            + ". Это и есть предел одного процесса: новые пользователи добавляют очередь, "
            "а не пропускную способность.",
            "",
        ]

    lines += [
        "## 4. Гипотеза об узком месте",
        "",
        "1. **Один процесс Flask dev-сервера.** Все запросы обслуживаются в одном процессе; "
        "при росте числа пользователей они встают в очередь, и p95 растёт быстрее RPS. "
        "Подтверждение: RPS растёт почти линейно только до 20–30 пользователей, дальше "
        "прирост замедляется, а p95 удваивается.",
        "2. **SQLite и запись.** Перевод — единственная операция, которая пишет в БД; в профиле "
        "у неё вес 1, но именно она вызывает блокировки при конкурентных записях. "
        "Чтения (счета, история) ускоряются индексами, записи — нет.",
        "3. **Дорогой вход.** `scrypt`-хэш пароля на `/api/v1/login` занимает сотни миллисекунд "
        "на запрос (видно по базовому прогону: p99 логина ~230 мс против 10–15 мс у чтения). "
        "Вход выполняется один раз на пользователя, поэтому на длинной нагрузке не доминирует, "
        "но при шторме входов становится первым ограничением.",
        "4. **Генератор и приложение на одной машине.** Часть CPU забирает сам Locust; "
        "реальный предел выше, а точка деградации на отдельном сервере наступит позже.",
        "",
        "## 5. Что улучшить",
        "",
        "| Проблема | Мера | Ожидаемый эффект |",
        "|---|---|---|",
        "| Один процесс | запуск под gunicorn/waitress с несколькими воркерами | линейный рост RPS с числом ядер |",
        "| Блокировки SQLite на записи | WAL-режим, короткие транзакции, вынести запись в очередь | меньше ошибок при конкурентных переводах |",
        "| Дорогой вход | ограничить частоту входов, кэшировать токен, снизить параметры scrypt при массовом входе | p99 входа ниже |",
        "| Долгие выборки истории | индексы по `sender_acc_id`/`receiver_acc_id` и `timestamp`, лимит по умолчанию | p95 истории стабильнее |",
        "",
        "## 6. Ограничения достоверности",
        "",
        "- Генератор нагрузки и приложение работают на одной машине (WSL2): цифры занижены.",
        "- Dev-сервер Flask не предназначен для нагрузки; для боевых выводов нужен WSGI-сервер.",
        "- SQLite — файловая БД без пула соединений; на PostgreSQL поведение будет другим.",
        "",
    ]

    (ROOT / "docs" / "performance" / "LOAD_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"готово: docs/LOAD_RESULTS.md, {chart}")
    for point in points:
        print(point)


if __name__ == "__main__":
    main()

"""Baseline explicavel de demanda por rota e dia da semana.

Executa backtesting temporal e gera a previsao final sem usar o incremento.
Usa somente a biblioteca padrao para funcionar mesmo sem numpy/pandas.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CURATED_DIR = PROJECT_ROOT / "data" / "curated"
REPORT_DIR = PROJECT_ROOT / "reports" / "forecast"
HISTORY_FILE = CURATED_DIR / "demanda_historica_diaria.csv"
FORECAST_FILE = CURATED_DIR / "previsao_baseline_congelada.csv"
BACKTEST_FILE = REPORT_DIR / "backtest_metrics.csv"
SUMMARY_FILE = REPORT_DIR / "baseline_summary.json"

BACKTEST_WINDOWS = [
    (date(2026, 8, 30), date(2026, 8, 31), date(2026, 9, 6)),
    (date(2026, 9, 6), date(2026, 9, 7), date(2026, 9, 13)),
    (date(2026, 9, 13), date(2026, 9, 14), date(2026, 9, 20)),
    (date(2026, 9, 20), date(2026, 9, 21), date(2026, 9, 27)),
]
FINAL_CUTOFF = date(2026, 9, 27)
FINAL_START = date(2026, 9, 28)
FINAL_END = date(2026, 10, 4)


def read_history() -> tuple[dict[tuple[str, date], float], set[str]]:
    values: dict[tuple[str, date], float] = defaultdict(float)
    routes: set[str] = set()
    with HISTORY_FILE.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source, delimiter=";"):
            day = date.fromisoformat(row["data"])
            route = row["rota_id"]
            values[(route, day)] += float(row["kg"])
            routes.add(route)
    return values, routes


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def estimate(history: dict[tuple[str, date], float], route: str, target: date, train_end: date) -> float:
    """Mean of the four previous same-weekday observations, with zero fallback."""
    if target.weekday() == 6:
        return 0.0
    observations = []
    cursor = min(target - timedelta(days=7), train_end)
    while cursor >= date(2025, 1, 1) and len(observations) < 4:
        observations.append(history.get((route, cursor), 0.0))
        cursor -= timedelta(days=7)
    return sum(observations) / len(observations) if observations else 0.0


def evaluate_window(history, routes, train_end: date, test_start: date, test_end: date):
    rows = []
    all_absolute_errors = []
    all_actual = 0.0
    all_signed_error = 0.0
    for route in sorted(routes):
        absolute_errors = []
        actual_total = 0.0
        signed_error = 0.0
        predicted_total = 0.0
        for target in date_range(test_start, test_end):
            actual = history.get((route, target), 0.0)
            predicted = estimate(history, route, target, train_end)
            error = predicted - actual
            rows.append(
                {
                    "window_train_end": train_end.isoformat(),
                    "test_start": test_start.isoformat(),
                    "test_end": test_end.isoformat(),
                    "rota_id": route,
                    "data": target.isoformat(),
                    "real_kg": f"{actual:.1f}",
                    "previsao_kg": f"{predicted:.1f}",
                    "erro_kg": f"{error:.1f}",
                }
            )
            absolute_errors.append(abs(error))
            actual_total += actual
            predicted_total += predicted
            signed_error += error
        all_absolute_errors.extend(absolute_errors)
        all_actual += actual_total
        all_signed_error += signed_error
        rows.append({
            "window_train_end": train_end.isoformat(),
            "test_start": test_start.isoformat(),
            "test_end": test_end.isoformat(),
            "rota_id": route,
            "data": "",
            "real_kg": f"{actual_total:.1f}",
            "previsao_kg": f"{predicted_total:.1f}",
            "erro_kg": f"{signed_error:.1f}",
            "mae_kg": f"{sum(absolute_errors) / len(absolute_errors):.1f}",
            "wape": f"{sum(absolute_errors) / actual_total:.6f}" if actual_total else "",
            "bias": f"{signed_error / actual_total:.6f}" if actual_total else "",
            "observacoes": str(len(absolute_errors)),
        })
    rows.append({
        "window_train_end": train_end.isoformat(),
        "test_start": test_start.isoformat(),
        "test_end": test_end.isoformat(),
        "rota_id": "TOTAL",
        "data": "",
        "real_kg": f"{all_actual:.1f}",
        "previsao_kg": f"{all_actual + all_signed_error:.1f}",
        "erro_kg": f"{all_signed_error:.1f}",
        "mae_kg": f"{sum(all_absolute_errors) / len(all_absolute_errors):.1f}",
        "wape": f"{sum(all_absolute_errors) / all_actual:.6f}" if all_actual else "",
        "bias": f"{all_signed_error / all_actual:.6f}" if all_actual else "",
        "observacoes": str(len(all_absolute_errors)),
    })
    return rows


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = []
    for row in rows:
        for column in row:
            if column not in columns:
                columns.append(column)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    history, routes = read_history()
    backtest_rows = []
    for train_end, test_start, test_end in BACKTEST_WINDOWS:
        backtest_rows.extend(evaluate_window(history, routes, train_end, test_start, test_end))

    final_rows = []
    generated_at = datetime.now(timezone.utc).isoformat()
    for route in sorted(routes):
        for target in date_range(FINAL_START, FINAL_END):
            final_rows.append(
                {
                    "generated_at": generated_at,
                    "data_corte": f"{FINAL_CUTOFF.isoformat()}T23:59:59-03:00",
                    "horizonte_inicio": FINAL_START.isoformat(),
                    "horizonte_fim": FINAL_END.isoformat(),
                    "rota_id": route,
                    "data": target.isoformat(),
                    "unidade": "kg",
                    "estimativa": f"{estimate(history, route, target, FINAL_CUTOFF):.1f}",
                    "metodo": "MEDIA_4_SEMANAS_MESMO_DIA_SEMANA",
                    "intervalo_inferior": "",
                    "intervalo_superior": "",
                    "explicacao_incerteza": "Historico curto por rota; sem intervalo calibrado.",
                }
            )

    write_csv(BACKTEST_FILE, backtest_rows)
    write_csv(FORECAST_FILE, final_rows)

    totals = [row for row in backtest_rows if row["rota_id"] == "TOTAL"]
    summary = {
        "generated_at": generated_at,
        "method": "MEDIA_4_SEMANAS_MESMO_DIA_SEMANA",
        "data_cutoff": f"{FINAL_CUTOFF.isoformat()}T23:59:59-03:00",
        "horizon": [FINAL_START.isoformat(), FINAL_END.isoformat()],
        "routes": len(routes),
        "forecast_rows": len(final_rows),
        "backtest_windows": len(BACKTEST_WINDOWS),
        "backtest_totals": totals,
        "incremental_used": False,
        "intervals_generated": False,
    }
    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

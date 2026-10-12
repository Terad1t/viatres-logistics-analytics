"""Aplica o lote incremental de forma idempotente depois do congelamento."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = PROJECT_ROOT / "outputs" / "candidato" / "dados" / "base"
INCREMENTAL_DIR = PROJECT_ROOT / "outputs" / "candidato" / "dados" / "incremental"
CURATED_DIR = PROJECT_ROOT / "data" / "curated"
OUTPUT_DIR = PROJECT_ROOT / "data" / "incremental_snapshots"
REPORT_DIR = PROJECT_ROOT / "reports" / "quality"
BATCH = INCREMENTAL_DIR / "pedidos_lote_2026-09-28.csv"
FORECAST = CURATED_DIR / "previsao_baseline_congelada.csv"
SIMULATION_TIME = "2026-09-28T08:00:00-03:00"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source, delimiter=";"))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def selected_snapshot(rows: list[dict[str, str]], as_of: str) -> list[dict[str, str]]:
    selected = {}
    for row in rows:
        if row["atualizado_em"] <= as_of:
            current = selected.get(row["pedido_id"])
            if current is None or (row["atualizado_em"], int(row["versao"])) > (current["atualizado_em"], int(current["versao"])):
                selected[row["pedido_id"]] = row
    return [selected[key] for key in sorted(selected)]


def main() -> None:
    base_rows = read_csv(BASE_DIR / "pedidos.csv")
    batch_rows = read_csv(BATCH)
    before = selected_snapshot(base_rows, "2026-09-27T23:59:59-03:00")
    merged_once = {(row["pedido_id"], row["versao"]): row for row in base_rows}
    for row in batch_rows:
        merged_once[(row["pedido_id"], row["versao"])] = row
    merged_twice = dict(merged_once)
    for row in batch_rows:
        merged_twice[(row["pedido_id"], row["versao"])] = row
    after_rows = selected_snapshot(list(merged_once.values()), SIMULATION_TIME)
    after_reapply_rows = selected_snapshot(list(merged_twice.values()), SIMULATION_TIME)
    before_by_id = {row["pedido_id"]: row for row in before}
    after_by_id = {row["pedido_id"]: row for row in after_rows}
    changed = sorted(key for key in before_by_id.keys() & after_by_id.keys() if before_by_id[key] != after_by_id[key])
    new = sorted(after_by_id.keys() - before_by_id.keys())
    forecast_hash_before = sha256(FORECAST)
    write_csv(OUTPUT_DIR / "orders_snapshot_before_2026-09-28.csv", before)
    write_csv(OUTPUT_DIR / "orders_snapshot_after_2026-09-28.csv", after_rows)
    forecast_hash_after = sha256(FORECAST)
    summary = {
        "simulation_time": SIMULATION_TIME,
        "batch": BATCH.name,
        "batch_rows": len(batch_rows),
        "before_entities": len(before),
        "after_entities": len(after_rows),
        "changed_entities": changed,
        "new_entities": new,
        "reapply_is_idempotent": after_rows == after_reapply_rows,
        "forecast_hash_preserved": forecast_hash_before == forecast_hash_after,
        "forecast_hash": forecast_hash_before,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "incremental_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

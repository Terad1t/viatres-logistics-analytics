"""Reconcilia pedidos, carga embarcada e custos agregados."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = PROJECT_ROOT / "outputs" / "candidato" / "dados" / "base"
CURATED_DIR = PROJECT_ROOT / "data" / "curated"
REPORT_DIR = PROJECT_ROOT / "reports" / "quality"
CUTOFF = "2026-09-27"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source, delimiter=";"))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    orders = read_csv(CURATED_DIR / "pedidos_elegiveis.csv")
    bridge = read_csv(BASE_DIR / "viagem_pedidos.csv")
    trips = {row["viagem_id"]: row for row in read_csv(BASE_DIR / "viagens.csv")}
    raw_costs = read_csv(BASE_DIR / "custos.csv")
    costs = {row["viagem_id"]: row for row in read_csv(CURATED_DIR / "custos_por_viagem.csv")}

    historical_orders = {
        row["pedido_id"]: row
        for row in orders
        if row["status"] == "CONFIRMADO" and row["data_coleta"] <= CUTOFF
    }
    bridge_by_order = defaultdict(list)
    for row in bridge:
        if row["pedido_id"] in historical_orders and row["viagem_id"] in trips:
            bridge_by_order[row["pedido_id"]].append(row)

    order_load_rows = []
    total_requested = total_embarked = 0.0
    for order_id, order in historical_orders.items():
        links = bridge_by_order.get(order_id, [])
        requested = float(order["peso_kg"])
        embarked = sum(float(row["peso_embarcado_kg"]) for row in links)
        difference = embarked - requested
        total_requested += requested
        total_embarked += embarked
        if len(links) != 1 or abs(difference) > 0.1:
            order_load_rows.append({
                "pedido_id": order_id,
                "rota_id": order["rota_id_normalizada"],
                "data_coleta": order["data_coleta"],
                "peso_solicitado_kg": f"{requested:.1f}",
                "peso_embarcado_kg": f"{embarked:.1f}",
                "diferenca_kg": f"{difference:.1f}",
                "quantidade_viagens": len(links),
                "motivo": "SEM_PONTE" if not links else "MULTIPLAS_VIAGENS" if len(links) != 1 else "DIVERGENCIA_PESO",
            })

    cost_trip_ids = set(costs)
    trip_cost_rows = []
    for trip_id, trip in trips.items():
        if trip_id not in cost_trip_ids:
            trip_cost_rows.append({"viagem_id": trip_id, "motivo": "SEM_CUSTO_AGREGADO"})
    duplicate_groups = defaultdict(list)
    for row in raw_costs:
        duplicate_groups[row["lancamento_id"]].append(row)
    duplicate_cost_ids = {key for key, rows in duplicate_groups.items() if len(rows) > 1}
    valid_raw_costs = [row for row in raw_costs if row["lancamento_id"] not in duplicate_cost_ids and row["viagem_id"] in trips]
    raw_by_component = defaultdict(float)
    for row in valid_raw_costs:
        raw_by_component[row["componente"]] += float(row["valor_brl"])
    curated_by_component = {
        "VARIAVEL_PROPRIO": sum(float(row["custo_variavel_proprio_brl"]) for row in costs.values()),
        "FRETE_BASE": sum(float(row["frete_base_brl"]) for row in costs.values()),
        "ADICIONAL_EMERGENCIAL": sum(float(row["adicional_emergencial_brl"]) for row in costs.values()),
        "PEDAGIO": sum(float(row["pedagio_brl"]) for row in costs.values()),
    }
    component_rows = []
    for component in sorted(curated_by_component):
        raw_total = raw_by_component[component]
        curated_total = curated_by_component[component]
        component_rows.append({
            "componente": component,
            "bruto_valido_brl": f"{raw_total:.2f}",
            "curado_brl": f"{curated_total:.2f}",
            "diferenca_brl": f"{curated_total - raw_total:.2f}",
            "reconciliado": abs(curated_total - raw_total) <= 0.05,
            "tolerancia_brl": "0.05",
        })

    summary = {
        "historical_orders": len(historical_orders),
        "orders_with_reconciliation_issue": len(order_load_rows),
        "requested_kg": round(total_requested, 1),
        "embarked_kg": round(total_embarked, 1),
        "difference_kg": round(total_embarked - total_requested, 1),
        "cost_trip_count": len(costs),
        "trip_count": len(trips),
        "trips_without_aggregated_cost": len(trip_cost_rows),
        "duplicate_cost_ids_raw": len(duplicate_cost_ids),
        "cost_component_reconciled": all(row["reconciliado"] for row in component_rows),
        "tolerance_kg": 0.1,
        "tolerance_brl": 0.05,
    }
    write_csv(REPORT_DIR / "order_load_reconciliation.csv", order_load_rows)
    write_csv(REPORT_DIR / "trip_cost_reconciliation.csv", trip_cost_rows)
    write_csv(REPORT_DIR / "cost_component_reconciliation.csv", component_rows)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "reconciliation_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

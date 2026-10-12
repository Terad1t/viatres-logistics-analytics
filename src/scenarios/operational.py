"""Simula alternativas operacionais no horizonte congelado."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = PROJECT_ROOT / "outputs" / "candidato" / "dados" / "base"
CURATED_DIR = PROJECT_ROOT / "data" / "curated"
REPORT_DIR = PROJECT_ROOT / "reports" / "scenarios"
LOSS_DATE = date(2026, 9, 29)


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


def money(value: float) -> str:
    return f"{value:.2f}"


def main() -> None:
    routes = {row["rota_id"]: row for row in read_csv(BASE_DIR / "rotas.csv")}
    tariffs = {row["rota_id"]: row for row in read_csv(BASE_DIR / "tarifas.csv")}
    fleet = read_csv(BASE_DIR / "frota.csv")
    availability = read_csv(BASE_DIR / "disponibilidade.csv")
    capacity = {(row["data"], row["galpao_id"]): row for row in read_csv(BASE_DIR / "capacidade.csv")}
    forecast = read_csv(CURATED_DIR / "previsao_baseline_congelada.csv")

    fleet_by_base = defaultdict(list)
    for vehicle in fleet:
        fleet_by_base[vehicle["galpao_base_id"]].append(vehicle)
    available = defaultdict(list)
    for row in availability:
        if row["status"] == "DISPONIVEL" and float(row["horas_disponiveis"]) > 0:
            available[(row["data"], row["veiculo_id"])].append(row)

    rows = []
    scenarios = [
        ("BASE", 1.0, False),
        ("DEMANDA_MAIS_20_PCT", 1.2, False),
        ("PERDA_VEICULO_DISPONIVEL_2026-09-29", 1.0, True),
    ]
    own_allocations = {}
    for scenario, demand_factor, vehicle_loss in scenarios:
        for day_text in sorted({row["data"] for row in forecast}):
            day = date.fromisoformat(day_text)
            for warehouse, warehouse_fleet in fleet_by_base.items():
                remaining_vehicles = [
                    vehicle for vehicle in warehouse_fleet
                    if (day_text, vehicle["veiculo_id"]) in available
                ]
                if vehicle_loss and day == LOSS_DATE and remaining_vehicles:
                    remaining_vehicles = remaining_vehicles[1:]
                route_ids = sorted(
                    row["rota_id"] for row in forecast
                    if row["data"] == day_text and routes[row["rota_id"]]["galpao_origem_id"] == warehouse
                )
                for route_id in route_ids:
                    route = routes[route_id]
                    demand_kg = next(float(row["estimativa"]) for row in forecast if row["data"] == day_text and row["rota_id"] == route_id) * demand_factor
                    required_cycles = math.ceil(demand_kg / float(route["cap_kg"])) if demand_kg else 0
                    eligible = [
                        vehicle for vehicle in remaining_vehicles
                        if float(route["horas_ciclo"]) <= float(next(iter(available[(day_text, vehicle["veiculo_id"])]))["horas_disponiveis"])
                    ]
                    assigned = eligible[:required_cycles]
                    own_allocations[(scenario, day_text, route_id)] = len(assigned)
                    assigned_ids = {vehicle["veiculo_id"] for vehicle in assigned}
                    remaining_vehicles = [vehicle for vehicle in remaining_vehicles if vehicle["veiculo_id"] not in assigned_ids]
    for scenario, demand_factor, vehicle_loss in scenarios:
        for forecast_row in forecast:
            day = date.fromisoformat(forecast_row["data"])
            route_id = forecast_row["rota_id"]
            route = routes[route_id]
            tariff = tariffs[route_id]
            warehouse = route["galpao_origem_id"]
            demand_kg = float(forecast_row["estimativa"]) * demand_factor
            if day.weekday() == 6:
                demand_kg = 0.0
            cycle_capacity = float(route["cap_kg"])
            required_cycles = math.ceil(demand_kg / cycle_capacity) if demand_kg else 0
            own_cycles = own_allocations[(scenario, day.isoformat(), route_id)]
            remaining = max(required_cycles - own_cycles, 0)
            regular_limit = int(tariff["limite_regular_viagens_dia"])
            regular_cycles = min(remaining, regular_limit)
            emergency_cycles = max(remaining - regular_cycles, 0)
            own_cost = own_cycles * (float(route["km_ciclo"]) * float(fleet_by_base[warehouse][0]["custo_variavel_km_brl"]) + float(tariff["pedagio_ciclo_brl"]))
            regular_cost = regular_cycles * (float(tariff["frete_regular_ciclo_brl"]) + float(tariff["pedagio_ciclo_brl"]))
            emergency_cost = emergency_cycles * (float(tariff["frete_regular_ciclo_brl"]) * (1 + float(tariff["adicional_emergencial_pct"])) + float(tariff["pedagio_ciclo_brl"]))
            total_cost = own_cost + regular_cost + emergency_cost
            cap = capacity.get((day.isoformat(), warehouse))
            warehouse_capacity = float(cap["cap_kg_dia"]) if cap else None
            warehouse_utilization = demand_kg / warehouse_capacity if warehouse_capacity else None
            if day.weekday() == 6 and demand_kg == 0:
                feasibility = "SEM_COLETA_DOMINGO"
            elif warehouse_capacity is None:
                feasibility = "DADOS_CAPACIDADE_AUSENTES"
            elif warehouse_utilization > 1:
                feasibility = "NAO_VIAVEL_GARGALO_GALPAO"
            elif emergency_cycles:
                feasibility = "RISCO_DEPENDENCIA_EMERGENCIAL"
            else:
                feasibility = "VIAVEL_SOB_PREMISSAS"
            rows.append({
                "cenario": scenario,
                "data": day.isoformat(),
                "rota_id": route_id,
                "galpao_id": warehouse,
                "demanda_kg": f"{demand_kg:.1f}",
                "ciclos_teoricos": required_cycles,
                "ciclos_proprios": own_cycles,
                "ciclos_regulares": regular_cycles,
                "ciclos_emergenciais": emergency_cycles,
                "custo_proprio_brl": money(own_cost),
                "custo_regular_brl": money(regular_cost),
                "custo_emergencial_brl": money(emergency_cost),
                "custo_incremental_estimado_brl": money(total_cost),
                "capacidade_galpao_kg": f"{warehouse_capacity:.1f}" if warehouse_capacity is not None else "",
                "utilizacao_galpao_kg": f"{warehouse_utilization:.6f}" if warehouse_utilization is not None else "",
                "viabilidade": feasibility,
                "confianca": "MEDIA" if warehouse_capacity is not None and not emergency_cycles else "BAIXA",
                "premissas": "Frota propria primeiro; regular limitado por contrato; emergencial sem capacidade garantida; kg apenas.",
            })

    write_csv(REPORT_DIR / "scenarios.csv", rows)
    summary = {
        "horizon": ["2026-09-28", "2026-10-04"],
        "scenarios": [item[0] for item in scenarios],
        "rows": len(rows),
        "vehicle_loss_date": LOSS_DATE.isoformat(),
        "m3_and_palettes_modeled": False,
        "emergency_capacity_guaranteed": False,
        "outputs": ["scenarios.csv"],
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "scenario_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

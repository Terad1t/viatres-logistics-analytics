"""Calcula KPIs contratuais sobre as fontes curadas e operacionais."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = PROJECT_ROOT / "outputs" / "candidato" / "dados" / "base"
CURATED_DIR = PROJECT_ROOT / "data" / "curated"
REPORT_DIR = PROJECT_ROOT / "reports" / "kpis"
CUTOFF = date(2026, 9, 27)
HORIZON_START = date(2026, 9, 28)
HORIZON_END = date(2026, 10, 4)


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


def number(value: float) -> str:
    return f"{value:.1f}"


def days_between(start: date, end: date) -> int:
    return (end - start).days + 1


def metric(name, value, unit, numerator, denominator, population, start, end, coverage, notes):
    return {
        "kpi": name,
        "value": value,
        "unit": unit,
        "numerator": numerator,
        "denominator": denominator,
        "population": population,
        "period_start": start,
        "period_end": end,
        "coverage": coverage,
        "cutoff": "2026-09-27T23:59:59-03:00",
        "notes": notes,
    }


def main() -> None:
    routes = {row["rota_id"]: row for row in read_csv(BASE_DIR / "rotas.csv")}
    orders = read_csv(CURATED_DIR / "pedidos_elegiveis.csv")
    historical = read_csv(CURATED_DIR / "demanda_historica_diaria.csv")
    backlog = read_csv(CURATED_DIR / "carteira_confirmada_diaria.csv")
    trips = read_csv(BASE_DIR / "viagens.csv")
    bridge = read_csv(BASE_DIR / "viagem_pedidos.csv")
    deliveries = read_csv(BASE_DIR / "entregas.csv")
    availability = read_csv(BASE_DIR / "disponibilidade.csv")
    capacities = read_csv(BASE_DIR / "capacidade.csv")
    trip_costs = {row["viagem_id"]: row for row in read_csv(CURATED_DIR / "custos_por_viagem.csv")}
    forecast = read_csv(CURATED_DIR / "previsao_baseline_congelada.csv")

    metrics = []
    historical_kg = sum(float(row["kg"]) for row in historical)
    historical_m3 = sum(float(row["m3"]) for row in historical)
    historical_pallets = sum(float(row["paletes"]) for row in historical)
    metrics.extend([
        metric("demanda_historica", number(historical_kg), "kg", number(historical_kg), number(historical_kg), "pedidos confirmados elegiveis por data_coleta", "2025-01-01", CUTOFF.isoformat(), f"{len(historical)} agregados diarios", "Cancelados, duplicados e registros invalidos excluidos."),
        metric("demanda_historica", number(historical_m3), "m3", number(historical_m3), number(historical_m3), "pedidos confirmados elegiveis por data_coleta", "2025-01-01", CUTOFF.isoformat(), f"{len(historical)} agregados diarios", "Volume solicitado; nao e capacidade de armazenagem."),
        metric("demanda_historica", number(historical_pallets), "paletes", number(historical_pallets), number(historical_pallets), "pedidos confirmados elegiveis por data_coleta", "2025-01-01", CUTOFF.isoformat(), f"{len(historical)} agregados diarios", "Paletes solicitados."),
    ])
    backlog_kg = sum(float(row["kg"]) for row in backlog)
    metrics.append(metric("carteira_confirmada", number(backlog_kg), "kg", number(backlog_kg), number(backlog_kg), "pedidos confirmados com coleta posterior ao corte", "2026-09-28", "2026-10-02", f"{len(backlog)} agregados diarios", "Nao somar novamente a previsao manual total."))

    valid_trips = [row for row in trips if row["viagem_id"] in trip_costs]
    trip_start = min(date.fromisoformat(row["data_saida"]) for row in valid_trips)
    trip_end = max(date.fromisoformat(row["data_saida"]) for row in valid_trips)
    variable_cost = sum(float(trip_costs[row["viagem_id"]]["custo_variavel_operacional_brl"]) for row in valid_trips)
    fixed_days = days_between(trip_start, trip_end)
    fixed_cost = 420 * 48 * fixed_days
    trip_count = len({row["viagem_id"] for row in valid_trips})
    emergency_count = sum(row["modalidade"] == "EMERGENCIAL" for row in valid_trips)
    own_count = sum(row["modalidade"] == "PROPRIO" for row in valid_trips)
    costs_by_component = defaultdict(float)
    for row in trip_costs.values():
        for component, field in {
            "VARIAVEL_PROPRIO": "custo_variavel_proprio_brl",
            "FRETE_BASE": "frete_base_brl",
            "ADICIONAL_EMERGENCIAL": "adicional_emergencial_brl",
            "PEDAGIO": "pedagio_brl",
        }.items():
            costs_by_component[component] += float(row[field])
    metrics.extend([
        metric("custo_variavel_operacional", money(variable_cost), "BRL", money(variable_cost), str(trip_count), "viagens com custos validos", trip_start.isoformat(), trip_end.isoformat(), f"{trip_count}/{len(trips)} viagens", "Custos agregados por viagem; fixos excluidos."),
        metric("custo_fixo_comprometido", money(fixed_cost), "BRL", money(fixed_cost), str(fixed_days), "48 veiculos por dia corrido", trip_start.isoformat(), trip_end.isoformat(), f"{fixed_days} dias", "Custo fixo nao tratado como economia evitavel."),
        metric("custo_total_recorte", money(variable_cost + fixed_cost), "BRL", money(variable_cost + fixed_cost), str(trip_count), "viagens validas mais custo fixo do periodo", trip_start.isoformat(), trip_end.isoformat(), f"{trip_count}/{len(trips)} viagens", "Variavel + custo fixo comprometido."),
        metric("participacao_emergencial", f"{emergency_count / trip_count:.6f}", "fracao", str(emergency_count), str(trip_count), "viagens unicas", trip_start.isoformat(), trip_end.isoformat(), f"{trip_count} viagens", "Nao e percentual medio por rota."),
    ])
    for component, value in costs_by_component.items():
        metrics.append(metric(f"custo_componente_{component.lower()}", money(value), "BRL", money(value), str(trip_count), "lancamentos agregados por viagem", trip_start.isoformat(), trip_end.isoformat(), f"{trip_count} viagens", "Fonte: custos_por_viagem."))

    loads = defaultdict(lambda: {"kg": 0.0, "m3": 0.0, "paletes": 0.0})
    for row in bridge:
        loads[row["viagem_id"]]["kg"] += float(row["peso_embarcado_kg"])
        loads[row["viagem_id"]]["m3"] += float(row["volume_embarcado_m3"])
        loads[row["viagem_id"]]["paletes"] += float(row["paletes_embarcados"])
    capacity_totals = defaultdict(float)
    load_totals = defaultdict(float)
    for trip in valid_trips:
        trip_load = loads[trip["viagem_id"]]
        for unit in ("kg", "m3", "paletes"):
            load_totals[unit] += trip_load[unit]
            capacity_totals[unit] += float(trip[f"cap_{unit}"])
    for unit in ("kg", "m3", "paletes"):
        utilization = load_totals[unit] / capacity_totals[unit] if capacity_totals[unit] else None
        metrics.append(metric(f"ocupacao_{unit}", f"{utilization:.6f}" if utilization is not None else "", "fracao", number(load_totals[unit]), number(capacity_totals[unit]), "viagens com carga e capacidade validas", trip_start.isoformat(), trip_end.isoformat(), f"{len(valid_trips)} viagens", "Razao entre somas; nao media simples de percentuais."))
    if load_totals["kg"]:
        metrics.extend([
            metric("custo_por_kg_expedido", money(variable_cost / load_totals["kg"]), "BRL/kg", money(variable_cost), number(load_totals["kg"]), "viagens com custo e carga validos", trip_start.isoformat(), trip_end.isoformat(), f"{len(valid_trips)} viagens", "Custo variavel dividido pelo peso embarcado do mesmo escopo."),
            metric("adicional_emergencial_por_kg", money(costs_by_component["ADICIONAL_EMERGENCIAL"] / load_totals["kg"]), "BRL/kg", money(costs_by_component["ADICIONAL_EMERGENCIAL"]), number(load_totals["kg"]), "viagens com custo e carga validos", trip_start.isoformat(), trip_end.isoformat(), f"{len(valid_trips)} viagens", "Nao inclui custos fixos."),
        ])

    available_vehicle_days = [row for row in availability if row["data"] <= CUTOFF.isoformat() and row["status"] == "DISPONIVEL" and float(row["horas_disponiveis"]) > 0]
    used_vehicle_days = {(row["data_saida"], row["veiculo_id"]) for row in trips if row["modalidade"] == "PROPRIO" and row["veiculo_id"] and row["data_saida"] <= CUTOFF.isoformat()}
    available_keys = {(row["data"], row["veiculo_id"]) for row in available_vehicle_days}
    used_available = len(used_vehicle_days & available_keys)
    available_count = len(available_keys)
    idle_count = max(available_count - used_available, 0)
    metrics.extend([
        metric("utilizacao_frota", f"{used_available / available_count:.6f}" if available_count else "", "fracao", str(used_available), str(available_count), "veiculos-dia comprovadamente disponiveis", "2025-01-01", CUTOFF.isoformat(), f"{available_count}/{len(availability)} linhas de disponibilidade", "Ausencias nao foram tratadas como disponibilidade."),
        metric("ociosidade_disponivel", f"{idle_count / available_count:.6f}" if available_count else "", "fracao", str(idle_count), str(available_count), "veiculos-dia comprovadamente disponiveis sem viagem", "2025-01-01", CUTOFF.isoformat(), f"{available_count}/{len(availability)} linhas de disponibilidade", "Nao e economia automaticamente evitavel."),
    ])

    order_by_id = {row["pedido_id"]: row for row in orders}
    delivery_by_order = {row["pedido_id"]: row for row in deliveries}
    bridge_order_ids = {row["pedido_id"] for row in bridge}
    service_orders = [row for row in orders if row["status"] == "CONFIRMADO" and row["data_coleta"] <= CUTOFF.isoformat() and row["data_prometida"] <= CUTOFF.isoformat() and row["pedido_id"] in bridge_order_ids]
    on_time = 0
    otif = 0
    backlog_overdue = 0
    service_missing = 0
    for order in service_orders:
        delivery = delivery_by_order.get(order["pedido_id"])
        if not delivery:
            service_missing += 1
            backlog_overdue += 1
            continue
        delivered_date = delivery["data_entrega"]
        complete = delivery["status"] == "ENTREGUE" and float(delivery["peso_entregue_kg"]) >= float(order["peso_kg"]) - 0.1
        timely = bool(delivered_date) and delivered_date <= order["data_prometida"]
        if timely:
            on_time += 1
        if timely and complete:
            otif += 1
        if delivery["status"] not in ("ENTREGUE", "PARCIAL"):
            backlog_overdue += 1
    service_denominator = len(service_orders)
    service_coverage = f"{service_denominator - service_missing}/{service_denominator}" if service_denominator else "0/0"
    metrics.extend([
        metric("entrega_no_prazo", f"{on_time / service_denominator:.6f}" if service_denominator else "", "fracao", str(on_time), str(service_denominator), "pedidos expedidos com promessa ate o corte", "2025-01-01", CUTOFF.isoformat(), service_coverage, "Pendente vencido conta como falha."),
        metric("otif", f"{otif / service_denominator:.6f}" if service_denominator else "", "fracao", str(otif), str(service_denominator), "pedidos expedidos com promessa ate o corte", "2025-01-01", CUTOFF.isoformat(), service_coverage, "Peso integral com tolerancia de 0.1 kg."),
        metric("backlog_vencido", str(backlog_overdue), "pedidos", str(backlog_overdue), str(service_denominator), "pedidos com promessa ate o corte sem entrega encerrada", "2025-01-01", CUTOFF.isoformat(), service_coverage, "PARCIAL e encerrada neste case."),
    ])

    capacity_by_day = {(row["data"], row["galpao_id"]): row for row in capacities if row["data"] >= HORIZON_START.isoformat() and row["data"] <= HORIZON_END.isoformat()}
    forecast_by_warehouse = defaultdict(float)
    for row in forecast:
        route = routes[row["rota_id"]]
        warehouse = route["galpao_origem_id"]
        forecast_by_warehouse[(row["data"], warehouse)] += float(row["estimativa"])
    capacity_rows = []
    for (day, warehouse), demand_kg in sorted(forecast_by_warehouse.items()):
        capacity = capacity_by_day.get((day, warehouse))
        cap_kg = float(capacity["cap_kg_dia"]) if capacity else None
        utilization = demand_kg / cap_kg if cap_kg else None
        alert = "SEM_CAPACIDADE" if capacity is None else "SEM_CAPACIDADE_UTILIZAVEL" if utilization is None else "CRITICO" if utilization > 1 else "SATURACAO" if utilization >= 0.9 else "NORMAL"
        capacity_rows.append({"data": day, "galpao_id": warehouse, "demanda_prevista_kg": number(demand_kg), "cap_kg_dia": number(cap_kg) if cap_kg is not None else "", "utilizacao_kg": f"{utilization:.6f}" if utilization is not None else "", "alerta": alert, "capacidade_m3_status": "NAO_CALCULADA_SEM_PREVISAO_M3"})
    write_csv(REPORT_DIR / "capacidade_prevista_diaria.csv", capacity_rows)

    write_csv(REPORT_DIR / "kpis.csv", metrics)
    summary = {"cutoff": "2026-09-27T23:59:59-03:00", "kpis": len(metrics), "capacity_rows": len(capacity_rows), "service_denominator": service_denominator, "service_missing": service_missing, "outputs": ["kpis.csv", "capacidade_prevista_diaria.csv"]}
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "kpi_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

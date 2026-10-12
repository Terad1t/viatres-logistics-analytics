from __future__ import annotations

import csv
import json
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs" / "candidato" / "dados" / "base"
CURATED = ROOT / "data" / "curated"
REPORTS = ROOT / "reports"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source, delimiter=";"))


class PipelineContractTests(unittest.TestCase):
    def test_reconciliation_is_zero(self):
        summary = json.loads((REPORTS / "quality" / "reconciliation_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["difference_kg"], 0.0)
        self.assertEqual(summary["orders_with_reconciliation_issue"], 0)
        self.assertEqual(summary["trips_without_aggregated_cost"], 0)
        self.assertTrue(summary["cost_component_reconciled"])

    def test_historical_and_backlog_respect_cutoff(self):
        historical = read_csv(CURATED / "demanda_historica_diaria.csv")
        backlog = read_csv(CURATED / "carteira_confirmada_diaria.csv")
        self.assertTrue(all(row["data"] <= "2026-09-27" for row in historical))
        self.assertTrue(all(row["data"] > "2026-09-27" for row in backlog))

    def test_costs_have_one_row_per_trip(self):
        costs = read_csv(CURATED / "custos_por_viagem.csv")
        trip_ids = [row["viagem_id"] for row in costs]
        self.assertEqual(len(trip_ids), len(set(trip_ids)))
        self.assertEqual(len(costs), 8517)

    def test_frozen_forecast_has_fixed_horizon_and_zero_sunday(self):
        forecast = read_csv(CURATED / "previsao_baseline_congelada.csv")
        self.assertEqual(len(forecast), 84)
        self.assertEqual({row["data_corte"] for row in forecast}, {"2026-09-27T23:59:59-03:00"})
        self.assertEqual({row["unidade"] for row in forecast}, {"kg"})
        sunday = [row for row in forecast if date.fromisoformat(row["data"]).weekday() == 6]
        self.assertTrue(sunday)
        self.assertTrue(all(float(row["estimativa"]) == 0 for row in sunday))

    def test_backtest_has_four_total_windows(self):
        rows = read_csv(REPORTS / "forecast" / "backtest_metrics.csv")
        totals = [row for row in rows if row["rota_id"] == "TOTAL"]
        self.assertEqual(len(totals), 4)
        self.assertEqual({row["observacoes"] for row in totals}, {"84"})

    def test_scenarios_have_expected_population_and_no_sunday_cycles(self):
        rows = read_csv(REPORTS / "scenarios" / "scenarios.csv")
        self.assertEqual(len(rows), 252)
        self.assertEqual({row["cenario"] for row in rows}, {"BASE", "DEMANDA_MAIS_20_PCT", "PERDA_VEICULO_DISPONIVEL_2026-09-29"})
        sunday = [row for row in rows if date.fromisoformat(row["data"]).weekday() == 6]
        self.assertTrue(sunday)
        self.assertTrue(all(int(row["ciclos_teoricos"]) == 0 for row in sunday))
        self.assertTrue(all(int(row["ciclos_proprios"]) == 0 for row in sunday))

    def test_raw_quality_source_was_not_modified(self):
        summary = json.loads((REPORTS / "quality" / "quality_summary.json").read_text(encoding="utf-8"))
        self.assertFalse(summary["raw_files_modified"])
        self.assertTrue((BASE / "pedidos.csv").exists())

    def test_incremental_is_idempotent_and_preserves_forecast(self):
        summary = json.loads((REPORTS / "quality" / "incremental_summary.json").read_text(encoding="utf-8"))
        self.assertTrue(summary["reapply_is_idempotent"])
        self.assertTrue(summary["forecast_hash_preserved"])
        self.assertEqual(summary["changed_entities"], ["P0043909"])
        self.assertEqual(summary["new_entities"], ["P9000001"])

    def test_executive_dashboard_was_generated(self):
        dashboard = REPORTS / "executive" / "dashboard.html"
        content = dashboard.read_text(encoding="utf-8")
        self.assertIn("Cockpit executivo", content)
        self.assertIn("Decidir antes do gargalo", content)
        self.assertIn("Alertas de capacidade", content)


if __name__ == "__main__":
    unittest.main()

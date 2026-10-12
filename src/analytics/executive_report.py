"""Gera um registro executivo de fatos, riscos e acoes sugeridas."""

from __future__ import annotations

import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
KPI_DIR = PROJECT_ROOT / "reports" / "kpis"
SCENARIO_DIR = PROJECT_ROOT / "reports" / "scenarios"
QUALITY_DIR = PROJECT_ROOT / "reports" / "quality"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "executive"


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
    kpis = read_csv(KPI_DIR / "kpis.csv")
    capacity = read_csv(KPI_DIR / "capacidade_prevista_diaria.csv")
    scenarios = read_csv(SCENARIO_DIR / "scenarios.csv")
    quality = json.loads((QUALITY_DIR / "quality_summary.json").read_text(encoding="utf-8"))
    reconciliation = json.loads((QUALITY_DIR / "reconciliation_summary.json").read_text(encoding="utf-8"))

    kpi_map = {(row["kpi"], row["unit"]): row for row in kpis}
    critical_capacity = [row for row in capacity if row["alerta"] == "CRITICO"]
    saturation_capacity = [row for row in capacity if row["alerta"] == "SATURACAO"]
    stress_emergency = [row for row in scenarios if row["cenario"] == "DEMANDA_MAIS_20_PCT" and int(row["ciclos_emergenciais"]) > 0]
    loss_emergency = [row for row in scenarios if row["cenario"].startswith("PERDA_VEICULO") and int(row["ciclos_emergenciais"]) > 0]

    actions = [
        {
            "prioridade": "P1",
            "tipo": "APROVACAO_EXECUTIVA",
            "fato_ou_hipotese": "PREVISAO",
            "assunto": "Capacidade do G01",
            "evidencia": f"{len(critical_capacity)} dias criticos e {len(saturation_capacity)} dias em saturacao por kg no horizonte.",
            "acao_sugerida": "Validar redistribuicao de janela, capacidade de doca e plano de expedicao para G01 antes de confirmar a semana.",
            "responsavel_sugerido": "Operacao de galpoes",
            "prazo": "Antes de 2026-09-28",
            "aprovacao": "Diretoria de Operacoes",
            "confianca": "MEDIA",
            "limitacao": "m3 e paletes da previsao ainda nao estao disponiveis.",
        },
        {
            "prioridade": "P1",
            "tipo": "RESERVA_OPERACIONAL",
            "fato_ou_hipotese": "CENARIO",
            "assunto": "Contingencia de transporte sob estresse",
            "evidencia": f"{len(stress_emergency)} linhas exigem ciclos emergenciais no cenario de demanda +20%.",
            "acao_sugerida": "Validar capacidade real de terceiros antes do horizonte; o modelo nao exigiu emergencia, mas nao prova disponibilidade contratual.",
            "responsavel_sugerido": "Compras e transportes",
            "prazo": "Antes de 2026-09-28",
            "aprovacao": "Gerencia de Transportes",
            "confianca": "BAIXA",
            "limitacao": "Nao ha capacidade contratual emergencial fornecida.",
        },
        {
            "prioridade": "P2",
            "tipo": "CONTINGENCIA",
            "fato_ou_hipotese": "CENARIO",
            "assunto": "Perda de veiculo em 2026-09-29",
            "evidencia": f"{len(loss_emergency)} linhas exigem emergencia apos a perda de um veiculo disponivel por galpao.",
            "acao_sugerida": "Confirmar disponibilidade por galpao e manter alternativa regular preparada; o modelo nao exigiu emergencia nesse estresse.",
            "responsavel_sugerido": "Planejamento de frota",
            "prazo": "2026-09-28",
            "aprovacao": "Gerencia de Operacoes",
            "confianca": "MEDIA",
            "limitacao": "O cenario usa somente kg e nao roteiriza paradas.",
        },
        {
            "prioridade": "P2",
            "tipo": "MONITORAMENTO",
            "fato_ou_hipotese": "HISTORICO",
            "assunto": "Nivel de servico",
            "evidencia": f"OTIF de {float(kpi_map[('otif', 'fracao')]['value']) * 100:.2f}% e entrega no prazo de {float(kpi_map[('entrega_no_prazo', 'fracao')]['value']) * 100:.2f}%.",
            "acao_sugerida": "Acompanhar OTIF por rota e coorte de promessa durante o piloto; nao declarar economia sem contrafactual financeiro.",
            "responsavel_sugerido": "Customer service e Operacao",
            "prazo": "Semanal",
            "aprovacao": "Nenhuma",
            "confianca": "ALTA",
            "limitacao": "O recorte historico nao prova causalidade de economia.",
        },
        {
            "prioridade": "P3",
            "tipo": "GOVERNANCA",
            "fato_ou_hipotese": "QUALIDADE",
            "assunto": "Achados de dados",
            "evidencia": f"{quality['findings']} achados em {quality['files']} arquivos; reconciliacao historica fecha em {reconciliation['difference_kg']:.1f} kg.",
            "acao_sugerida": "Manter quarentena e revisar os registros invalidos com os donos das fontes antes de ampliar a automatizacao.",
            "responsavel_sugerido": "Dados e donos das fontes",
            "prazo": "Antes do proximo ciclo",
            "aprovacao": "Data owner",
            "confianca": "ALTA",
            "limitacao": "Algumas regras ainda dependem de confirmacao operacional.",
        },
    ]

    write_csv(OUTPUT_DIR / "decision_register.csv", actions)
    summary = {
        "cutoff": "2026-09-27T23:59:59-03:00",
        "horizon": ["2026-09-28", "2026-10-04"],
        "recommendations": len(actions),
        "critical_capacity_rows": len(critical_capacity),
        "saturation_capacity_rows": len(saturation_capacity),
        "stress_emergency_rows": len(stress_emergency),
        "loss_emergency_rows": len(loss_emergency),
        "economic_savings_proven": False,
        "m3_and_palettes_in_scenarios": False,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "executive_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

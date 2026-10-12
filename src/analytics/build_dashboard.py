"""Gera uma visao executiva HTML sem dependencias externas."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS = PROJECT_ROOT / "reports"
OUTPUT = REPORTS / "executive" / "dashboard.html"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source, delimiter=";"))


def esc(value: object) -> str:
    return html.escape(str(value or ""))


def find_kpi(rows: list[dict[str, str]], name: str, unit: str = "") -> str:
    for row in rows:
        if row["kpi"] == name and (not unit or row["unit"] == unit):
            return row["value"]
    return "N/D"


def percent(value: str) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except ValueError:
        return "N/D"


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(item)}</th>" for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(item)}</td>" for item in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def main() -> None:
    kpis = read_csv(REPORTS / "kpis" / "kpis.csv")
    capacity = read_csv(REPORTS / "kpis" / "capacidade_prevista_diaria.csv")
    decisions = read_csv(REPORTS / "executive" / "decision_register.csv")
    scenarios = json.loads((REPORTS / "scenarios" / "scenario_summary.json").read_text(encoding="utf-8"))
    quality = json.loads((REPORTS / "quality" / "quality_summary.json").read_text(encoding="utf-8"))
    reconciliation = json.loads((REPORTS / "quality" / "reconciliation_summary.json").read_text(encoding="utf-8"))

    alerts = [row for row in capacity if row["alerta"] in {"CRITICO", "SATURACAO"}]
    alert_rows = [[row["data"], row["galpao_id"], percent(row["utilizacao_kg"]), row["alerta"]] for row in alerts]
    decision_rows = [[row["prioridade"], row["assunto"], row["acao_sugerida"], row["responsavel_sugerido"], row["prazo"]] for row in decisions]
    scenario_rows = [[row["cenario"], row["data"], row["rota_id"], row["ciclos_emergenciais"], row["viabilidade"]] for row in read_csv(REPORTS / "scenarios" / "scenarios.csv") if row["viabilidade"] != "VIAVEL_SOB_PREMISSAS"][:30]

    cards = [
        ("OTIF", percent(find_kpi(kpis, "otif", "fracao")), "historico"),
        ("Entrega no prazo", percent(find_kpi(kpis, "entrega_no_prazo", "fracao")), "historico"),
        ("Emergencial", percent(find_kpi(kpis, "participacao_emergencial", "fracao")), "8517 viagens"),
        ("Ocupacao kg", percent(find_kpi(kpis, "ocupacao_kg", "fracao")), "historico"),
        ("Achados de qualidade", quality["findings"], f"{quality['files']} arquivos"),
        ("Divergencia kg", reconciliation["difference_kg"], "reconciliacao"),
    ]
    card_html = "".join(f'<article class="card"><span>{esc(label)}</span><strong>{esc(value)}</strong><small>{esc(note)}</small></article>' for label, value, note in cards)
    alert_html = table(["Data", "Galpao", "Utilizacao kg", "Alerta"], alert_rows) if alert_rows else "<p>Nenhum alerta de capacidade no horizonte.</p>"
    decision_html = table(["Prioridade", "Assunto", "Acao", "Responsavel", "Prazo"], decision_rows)
    scenario_html = table(["Cenario", "Data", "Rota", "Ciclos emergenciais", "Viabilidade"], scenario_rows) if scenario_rows else "<p>Os cenarios nao geraram linhas fora de viabilidade sob as premissas atuais.</p>"

    document = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ViaTres | Cockpit executivo</title>
<style>
:root {{ --ink:#17211b; --muted:#66736a; --paper:#f5f2ea; --panel:#fffdf8; --line:#d9d6cb; --accent:#d06b3c; --green:#28634f; --red:#a83b32; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--paper); color:var(--ink); font:15px/1.5 Georgia,serif; }}
main {{ max-width:1200px; margin:0 auto; padding:40px 24px 64px; }}
header {{ display:flex; justify-content:space-between; gap:24px; align-items:end; border-bottom:2px solid var(--ink); padding-bottom:22px; }}
h1 {{ margin:0; font-size:clamp(2rem,5vw,4rem); line-height:1; letter-spacing:0; }} header p {{ margin:0; color:var(--muted); max-width:360px; }}
.meta {{ display:flex; gap:10px; flex-wrap:wrap; margin:20px 0 28px; }} .tag {{ border:1px solid var(--line); background:var(--panel); padding:6px 10px; font:12px ui-monospace,SFMono-Regular,Consolas,monospace; }}
.cards {{ display:grid; grid-template-columns:repeat(6,1fr); gap:12px; margin-bottom:36px; }} .card {{ background:var(--panel); border:1px solid var(--line); padding:16px; min-height:132px; display:flex; flex-direction:column; justify-content:space-between; }} .card span,.card small {{ color:var(--muted); }} .card strong {{ font-size:2rem; line-height:1; color:var(--green); }}
section {{ margin-top:34px; }} h2 {{ font-size:1.4rem; border-bottom:1px solid var(--line); padding-bottom:8px; }} h3 {{ margin-bottom:4px; }} .note {{ color:var(--muted); max-width:780px; }}
table {{ width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); }} th,td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }} th {{ background:#ebe8dd; font:12px ui-monospace,SFMono-Regular,Consolas,monospace; text-transform:uppercase; }} tr:last-child td {{ border-bottom:0; }}
.alert td:last-child {{ color:var(--red); font-weight:bold; }} .columns {{ display:grid; grid-template-columns:1fr 1fr; gap:28px; }} footer {{ border-top:1px solid var(--line); margin-top:42px; padding-top:14px; color:var(--muted); font-size:13px; }}
@media(max-width:900px) {{ .cards {{ grid-template-columns:repeat(3,1fr); }} header {{ display:block; }} header p {{ margin-top:16px; }} }} @media(max-width:600px) {{ main {{ padding:24px 14px 48px; }} .cards,.columns {{ grid-template-columns:1fr; }} table {{ display:block; overflow-x:auto; white-space:nowrap; }} .card strong {{ font-size:1.7rem; }} }}
</style></head>
<body><main>
<header><div><div class="tag">VIATRES / COCKPIT EXECUTIVO</div><h1>Decidir antes do gargalo.</h1></div><p>Visao de risco para a semana de 28/09 a 04/10/2026. Fatos, previsoes e hipoteses aparecem separados.</p></header>
<div class="meta"><span class="tag">Corte: 27/09/2026 23:59:59 -03:00</span><span class="tag">Atualizado: 12/10/2026</span><span class="tag">Previsao congelada antes do incremental</span></div>
<section><div class="cards">{card_html}</div></section>
<section><h2>Leitura rapida</h2><p class="note">G01 concentra os alertas de capacidade por kg. A previsao atual nao possui m3 ou paletes, portanto esses limites nao foram inferidos. A reconciliacao historica fecha em zero e a economia ainda nao e comprovada.</p></section>
<section><h2>Alertas de capacidade</h2>{alert_html}</section>
<section><h2>Decisoes recomendadas</h2>{decision_html}</section>
<section><h2>Cenarios fora do normal</h2>{scenario_html}</section>
<footer>Fonte: pipeline local ViaTres. Relatorio estatico gerado a partir de reports/. Nao substitui validacao operacional, disponibilidade contratual ou aprovacao financeira.</footer>
</main></body></html>"""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(document, encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT.relative_to(PROJECT_ROOT)), "alerts": len(alerts), "decisions": len(decisions), "scenario_exceptions": len(scenario_rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

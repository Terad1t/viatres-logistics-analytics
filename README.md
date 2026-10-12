
# ViaTres Logistics Analytics

Pipeline local e reproduzivel para diagnostico operacional, forecast de demanda, KPIs, cenarios de capacidade e apoio a decisoes executivas para a ViaTres Logistica.

## O que este projeto demonstra

- Validacao de contratos, chaves, dominios, datas e referencias.
- Quarentena de registros invalidos sem alterar o bruto.
- Selecao temporal de versoes de pedidos.
- Separacao entre demanda historica, carteira confirmada e previsao.
- Agregacao de custos por viagem antes dos joins analiticos.
- Backtesting temporal sem vazamento.
- Previsao congelada antes do lote incremental.
- KPIs de demanda, custo, capacidade, frota e servico.
- Cenarios operacionais com restricoes de frota e galpao.
- Simulacao incremental idempotente.
- Registro executivo de decisoes e cockpit HTML.

## Estado atual

O pipeline foi executado localmente e possui:

- 15 arquivos-base validados.
- 10 achados de qualidade documentados e preservados em quarentena.
- Reconciliacao historica de carga com diferenca de `0,0 kg`.
- Reconciliacao monetaria por componente com tolerancia de `R$ 0,05`.
- Forecast com quatro janelas de backtesting.
- Tres cenarios operacionais.
- Simulacao incremental idempotente.
- 9 testes automatizados aprovados.
- Dashboard executivo estatico em HTML.

## Requisitos

- Windows, macOS ou Linux.
- Node.js para validacao e curadoria.
- `uv` da Astral para os scripts Python.

O ambiente Python esta configurado por `pyproject.toml`, `uv.lock` e `.python-version`. Os scripts atuais usam a biblioteca padrao do Python para evitar dependencias nativas bloqueadas pela politica de Controle de Aplicativo do Windows.

## Execucao

Execute os comandos a partir da raiz do repositorio:

```powershell
node src\quality\validate_contracts.mjs
node src\quality\build_curated.mjs
& "$HOME\.local\bin\uv.exe" run python src\forecast\baseline.py
& "$HOME\.local\bin\uv.exe" run python src\analytics\kpis.py
& "$HOME\.local\bin\uv.exe" run python src\quality\reconcile_curated.py
& "$HOME\.local\bin\uv.exe" run python src\scenarios\operational.py
& "$HOME\.local\bin\uv.exe" run python src\analytics\executive_report.py
& "$HOME\.local\bin\uv.exe" run python src\analytics\build_dashboard.py
& "$HOME\.local\bin\uv.exe" run python src\quality\apply_incremental.py
& "$HOME\.local\bin\uv.exe" run python -m unittest discover -s tests -v
```

Se `uv` estiver no PATH, substitua `& "$HOME\.local\bin\uv.exe"` por `uv`.

O lote incremental deve ser aplicado somente depois de a previsao congelada ser gerada.

## Estrutura

```text
data/curated/                 tabelas analiticas curadas
data/incremental_snapshots/  snapshots antes e depois do lote
outputs/candidato/dados/base/ fontes CSV autoritativas
reports/quality/              inventario, achados, quarentena e reconciliacoes
reports/forecast/             backtesting e previsao
reports/kpis/                 indicadores e capacidade
reports/scenarios/            cenarios operacionais
reports/executive/            decisoes e dashboard
src/quality/                  contratos, curadoria e incremental
src/forecast/                 baseline e congelamento
src/analytics/                KPIs e relatorio executivo
src/scenarios/                simulacao operacional
tests/                        testes automatizados
```

## Artefatos principais

- [Dashboard executivo](reports/executive/dashboard.html)
- [Registro de decisoes](reports/executive/decision_register.csv)
- [Previsao congelada](data/curated/previsao_baseline_congelada.csv)
- [KPIs](reports/kpis/kpis.csv)
- [Cenarios](reports/scenarios/scenarios.csv)
- [Relatorio de qualidade](reports/quality/quality_findings.csv)
- [Guia de reproducao](outputs/candidato/documentacao/06_STATUS_EXECUCAO_E_REPRODUCAO.md)

## Principais limitacoes

- A previsao atual esta em kg; m3 e paletes ainda nao entram nos cenarios.
- A disponibilidade real de transportadoras emergenciais nao foi fornecida.
- O forecast e um baseline explicavel, nao uma garantia de desempenho futuro.
- Economia potencial nao e economia realizada; falta contrafactual financeiro validado.
- O holdout e a area `avaliador_RESTRITO` nao participam do pipeline candidato.
- O dashboard e estatico e deve ser regenerado quando os relatorios mudarem.

## Documentacao completa

Consulte [06_STATUS_EXECUCAO_E_REPRODUCAO.md](outputs/candidato/documentacao/06_STATUS_EXECUCAO_E_REPRODUCAO.md) para o inventario detalhado, regras de negocio, resultados, limitacoes e proxima sequencia de trabalho.

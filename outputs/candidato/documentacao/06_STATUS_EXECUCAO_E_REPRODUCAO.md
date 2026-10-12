# ViaTres Logistica - Status, execucao e reproducao

Este documento registra o estado real do projeto, o que foi implementado, o que ainda falta, as ferramentas usadas, as decisoes tecnicas e o modo de reproduzir os resultados.

O projeto e um exercicio local e ficticio de engenharia de dados, analytics, forecast e planejamento logistico.

## 1. Objetivo do projeto

Construir uma base analitica reproduzivel para apoiar decisoes semanais sobre:

- demanda realizada, carteira confirmada e previsao;
- gargalos por galpao, rota e dia;
- capacidade em kg, m3, paletes e horas;
- uso de frota propria, frete regular e frete emergencial;
- custo operacional e custo incremental;
- risco de atraso e OTIF;
- cenarios de aumento de demanda e perda de veiculo;
- acoes que exigem aprovacao executiva.

O corte de conhecimento e `2026-09-27 23:59:59`, no fuso `America/Sao_Paulo`.

O horizonte de decisao e `2026-09-28` a `2026-10-04`.

A data atual do computador nao deve mudar o relogio do exercicio. O case usa datas fixas.

## 2. Estrutura efetivamente usada

### Fontes

`outputs/candidato/dados/base/`

Contem os 15 CSVs-base autoritativos:

- `galpoes.csv`: cadastro de galpoes.
- `rotas.csv`: rotas, origem, distancia, horas, SLA e capacidades.
- `frota.csv`: veiculos proprios e seus limites.
- `tarifas.csv`: frete regular, adicional emergencial, pedagio e limites.
- `calendario.csv`: calendario operacional.
- `disponibilidade.csv`: status e horas disponiveis por veiculo/dia.
- `capacidade.csv`: capacidade efetiva de cada galpao/dia.
- `eventos_planejados.csv`: evento comercial conhecido.
- `pedidos.csv`: pedidos e versoes.
- `viagens.csv`: viagens realizadas ou planejadas.
- `viagem_pedidos.csv`: ponte entre viagens e pedidos.
- `entregas.csv`: status e resultado de entrega.
- `custos.csv`: lancamentos de custo por viagem.
- `previsao_manual.csv`: previsoes manuais por rota e semana.
- `aliases_rotas.csv`: aliases autorizados de rotas.

`outputs/candidato/dados/incremental/`

Contem o lote posterior ao corte. Ele possui uma nova versao de pedido e um pedido recebido com atraso. Ainda nao foi aplicado ao pipeline final porque a simulacao incremental deve ocorrer somente depois de a previsao estar congelada.

### Codigo

`src/quality/`

- `validate_contracts.mjs`: valida schemas, chaves, dominios, datas, referencias e regras condicionais; gera inventario, achados e quarentena.
- `build_curated.mjs`: aplica a politica de qualidade, seleciona pedidos elegiveis, normaliza rotas, separa demanda/carteira e agrega custos por viagem.
- `reconcile_curated.py`: reconcilia pedidos historicos com carga embarcada e verifica cobertura de custos.

`src/forecast/`

- `baseline.py`: baseline temporal por rota, usando a media das quatro ocorrencias anteriores do mesmo dia da semana; executa backtesting e gera previsao congelada.

`src/analytics/`

- `kpis.py`: calcula demanda, custos, ocupacao, frota, servico, OTIF, backlog e capacidade prevista.
- `executive_report.py`: transforma os resultados em um registro de decisoes com prioridade, evidencia, responsavel, prazo, aprovacao, confianca e limitacoes.

`src/scenarios/`

- `operational.py`: simula cenario-base, aumento de 20% na demanda e perda de um veiculo comprovadamente disponivel por galpao em `2026-09-29`.

### Dados curados

`data/curated/`

- `pedidos_elegiveis.csv`: versao elegivel dos pedidos no corte.
- `demanda_historica_diaria.csv`: demanda confirmada historica agregada por data, rota e galpao.
- `carteira_confirmada_diaria.csv`: pedidos confirmados com coleta posterior ao corte.
- `custos_por_viagem.csv`: custos agregados por viagem e componente.
- `previsao_manual_elegivel.csv`: previsoes manuais com alias resolvido, versao selecionada e unidade convertida.
- `previsao_baseline_congelada.csv`: previsao estatistica final para o horizonte.

### Relatorios

`reports/quality/`

- `inventory.csv`: inventario dos arquivos-base.
- `quality_findings.csv`: achados por arquivo, linha, regra e campo.
- `quality_summary.json`: resumo da validacao.
- `curation_summary.json`: contagens da curadoria e exclusoes.
- `reconciliation_summary.json`: resultado da reconciliacao.
- `order_load_reconciliation.csv`: pedidos com divergencia entre solicitado e embarcado.
- `trip_cost_reconciliation.csv`: viagens sem custo agregado.
- `cost_component_reconciliation.csv`: comparacao monetaria por componente com tolerancia de R$ 0,05.
- `quarantine/`: copias dos registros com achados.

`reports/forecast/`

- `backtest_metrics.csv`: metricas por janela e rota.
- `baseline_summary.json`: resumo do metodo, corte, horizonte e metricas.

`reports/kpis/`

- `kpis.csv`: indicadores em formato longo, com unidade, numerador, denominador, cobertura e corte.
- `capacidade_prevista_diaria.csv`: previsao em kg por galpao/dia, capacidade efetiva, utilizacao e alerta.
- `kpi_summary.json`: resumo da execucao.

`reports/scenarios/`

- `scenarios.csv`: resultado detalhado dos tres cenarios.
- `scenario_summary.json`: resumo da simulacao e limitacoes.

`reports/executive/`

- `decision_register.csv`: recomendacoes executivas rastreaveis.
- `executive_summary.json`: contagem e principais alertas.
- `dashboard.html`: cockpit executivo estatico gerado a partir dos relatorios.

`tests/`

- `test_pipeline.py`: oito testes de contrato sobre reconciliacao, corte, custos, forecast, domingos, cenarios, imutabilidade do bruto e incremental.

### Documentacao

- `00_GUIA_JUNIOR.md`: explicacao introdutoria do projeto.
- `01_BRIEFING_CEO.md`: necessidades da diretoria.
- `02_DESAFIO_E_EXECUCAO.md`: escopo e forma de execucao.
- `02_POLITICA_QUALIDADE.md`: tratamento dos achados e exclusoes.
- `03_DICIONARIO_E_CONTRATOS.md`: granularidades, chaves e regras de negocio.
- `04_KPIS_E_LIMITES.md`: definicoes dos indicadores e limites de interpretacao.
- `05_VALIDACAO_E_ACEITE.md`: criterios de aceite e rubrica.
- `dicionario_dados.csv`: contrato campo a campo.

## 3. O que ja foi feito

### Etapa 1 - Inventario e entendimento

Concluida.

- Foram confirmados 15 CSVs-base.
- Foram encontrados os arquivos incrementais.
- As copias dos tres pacotes foram comparadas por SHA-256.
- A fonte de trabalho escolhida foi `outputs/candidato/dados/base/`.
- A area `avaliador_RESTRITO` foi mantida fora do pipeline.
- Schemas, granularidades, chaves e relacionamentos foram documentados.

### Etapa 2 - Contratos e qualidade

Implementada e executada.

A validacao encontrou 10 achados atuais:

- 4 ocorrencias relacionadas a chaves duplicadas, cobrindo duplicidades em pedidos e custos;
- 1 medida fisica negativa;
- 1 campo obrigatorio ausente;
- 1 data de calendario invalida;
- 1 valor fora do dominio;
- 2 referencias estrangeiras inexistentes.

O bruto nao foi alterado. Os registros problematicos sao copiados para quarentena.

A politica atual e:

- nao corrigir por adivinhacao;
- excluir duplicidades da camada curada;
- excluir pedidos sem rota valida;
- excluir medidas fisicas negativas;
- aceitar `t` na previsao manual e converter por `1 t = 1000 kg`;
- aceitar viagem terceirizada sem veiculo;
- aceitar entrega `EM_TRANSITO` sem data e peso.

### Etapa 3 - Curadoria

Implementada e executada.

Resultados atuais:

- 44.005 pedidos selecionados;
- 5 pedidos excluidos;
- 6.528 agregados diarios de demanda historica;
- 56 agregados diarios de carteira;
- 18.292 lancamentos de custo validos;
- 8.517 viagens com custos agregados;
- 36 previsoes manuais elegiveis.

Custos sao agregados por viagem e componente antes de qualquer uso analitico.

### Etapa 4 - Forecast e backtesting

Baseline implementado e executado.

Metodo:

- media das quatro ocorrencias anteriores do mesmo dia da semana;
- uma serie independente por rota;
- domingos com demanda contratual zero;
- nenhum uso do lote incremental;
- quatro janelas temporais conforme contrato;
- previsao final congelada no horizonte de 28/09 a 04/10.

Metricas agregadas do backtesting:

- WAPE entre 17,13% e 19,63%;
- viés entre -6,24% e +1,10%;
- MAE entre 1.091 kg e 1.195 kg.

Nao foram gerados intervalos de previsao porque ainda nao existe calibracao suficiente para declarar cobertura.

### Etapa 5 - KPIs

Implementada e executada.

Indicadores atuais incluem:

- demanda historica em kg, m3 e paletes;
- carteira confirmada;
- custo variavel;
- custo fixo comprometido;
- custo total;
- custo por kg;
- adicional emergencial por kg;
- participacao emergencial;
- ocupacao em kg, m3 e paletes;
- utilizacao e ociosidade da frota;
- entrega no prazo;
- OTIF;
- backlog vencido;
- capacidade prevista em kg por galpao/dia.

Resultados principais:

- OTIF: 88,36%;
- entrega no prazo: 90,59%;
- participacao emergencial: 14,79%;
- ocupacao agregada em kg: 57,40%.

### Etapa 6 - Cenarios

Implementada e executada.

Cenarios:

1. Base.
2. Demanda 20% maior.
3. Perda de um veiculo disponivel por galpao em 29/09.

A alocacao respeita um ciclo por veiculo/dia, base fixa, horas disponiveis, limite regular e frota propria antes de terceiros.

Os cenarios nao modelam m3 ou paletes porque a previsao atual esta disponivel apenas em kg. A capacidade emergencial tambem nao e tratada como garantida.

### Etapa 7 - Reconciliacao

Concluida para o escopo historico elegivel.

- Peso solicitado: 39.104.298,6 kg.
- Peso embarcado: 39.104.298,6 kg.
- Diferenca: 0,0 kg.
- Pedidos com divergencia: 0.
- Viagens sem custo agregado: 0.

Tambem foi executada a reconciliacao monetaria por componente:

- `VARIAVEL_PROPRIO`, `FRETE_BASE`, `ADICIONAL_EMERGENCIAL` e `PEDAGIO` reconciliados;
- tolerancia aplicada: R$ 0,05;
- 1 chave de lancamento duplicada no bruto, tratada pela politica de quarentena.

### Etapa 8 - Registro executivo

Implementada.

O registro contem 5 recomendacoes. A principal e tratar G01 como ponto de aprovacao operacional, pois existem 2 dias criticos e 1 dia em saturacao por kg no horizonte.

O registro tambem deixa claro que:

- os cenarios de estresse nao exigiram emergencia no modelo;
- isso nao prova disponibilidade real de terceiros;
- economia realizada ainda nao foi comprovada;
- m3 e paletes precisam ser incluidos antes de uma decisao operacional definitiva.

### Etapa 9 - Testes automatizados

Implementada e executada com `unittest`.

Resultado atual: 8 testes executados e 8 aprovados.

Os testes cobrem:

- reconciliacao de pedidos e carga;
- corte entre historico e carteira;
- uma linha de custo agregada por viagem;
- horizonte e domingo da previsao congelada;
- quatro totais de backtesting;
- populacao e domingos dos cenarios;
- preservacao dos arquivos brutos;
- idempotencia do lote e preservacao do hash da previsao congelada.

### Etapa 10 - Simulacao incremental

Implementada e executada depois do congelamento da previsao.

Resultado atual:

- 2 linhas no lote incremental;
- 1 entidade alterada: `P0043909`;
- 1 entidade nova: `P9000001`;
- reaplicacao idempotente: verdadeira;
- hash da previsao congelada preservado: verdadeiro.

### Etapa 11 - Interface executiva

Implementada como HTML estatico, sem dependencia externa de dashboard.

O cockpit apresenta:

- cards de OTIF, entrega no prazo, emergencial, ocupacao e qualidade;
- alertas de capacidade por galpao e dia;
- registro de decisoes, responsaveis e prazos;
- excecoes dos cenarios;
- corte, horizonte e limitacoes visiveis.

Arquivo gerado: `reports/executive/dashboard.html`.

## 4. Ferramentas usadas

### Node.js

Usado para validacao e curadoria de CSVs sem dependencia externa:

- parser CSV com suporte a campos entre aspas;
- validacao de contratos;
- quarentena;
- agregacao de pedidos e custos.

Comandos:

```powershell
node src\quality\validate_contracts.mjs
node src\quality\build_curated.mjs
```

### uv da Astral

O `uv` foi instalado na versao `0.13.0` em `C:\Users\dippe\.local\bin`.

A configuracao do projeto usa:

- `pyproject.toml`;
- `uv.lock`;
- `.python-version` com Python 3.14.

Para executar quando `uv` estiver no PATH:

```powershell
uv run python src\forecast\baseline.py
```

Na sessao atual, o caminho explicito e:

```powershell
& "$HOME\.local\bin\uv.exe" run python src\forecast\baseline.py
```

### Python

Os scripts Python atuais usam a biblioteca padrao para nao depender do `numpy`, pois o Windows bloqueou uma DLL cientifica por politica de Controle de Aplicativo.

O ambiente foi sincronizado com `uv sync`, mas importar `numpy`, `pandas` ou `scikit-learn` ainda falha por essa politica do sistema.

Scripts Python:

```powershell
& "$HOME\.local\bin\uv.exe" run python src\forecast\baseline.py
& "$HOME\.local\bin\uv.exe" run python src\analytics\kpis.py
& "$HOME\.local\bin\uv.exe" run python src\quality\reconcile_curated.py
& "$HOME\.local\bin\uv.exe" run python src\scenarios\operational.py
& "$HOME\.local\bin\uv.exe" run python src\analytics\executive_report.py
```

### Formato dos dados

- CSV UTF-8 com BOM quando aplicavel.
- Delimitador `;`.
- Decimal com ponto.
- IDs tratados como texto.
- Datas ISO.
- Timestamps com offset `-03:00`.
- Valores vazios tratados como desconhecidos, nao como zero automatico.

## 5. Execucao completa recomendada

Executar a partir da raiz do projeto:

```powershell
node src\quality\validate_contracts.mjs
node src\quality\build_curated.mjs
& "$HOME\.local\bin\uv.exe" run python src\forecast\baseline.py
& "$HOME\.local\bin\uv.exe" run python src\analytics\kpis.py
& "$HOME\.local\bin\uv.exe" run python src\quality\reconcile_curated.py
& "$HOME\.local\bin\uv.exe" run python src\scenarios\operational.py
& "$HOME\.local\bin\uv.exe" run python src\analytics\executive_report.py
```

A ordem importa:

1. qualidade valida a fonte;
2. curadoria aplica a politica;
3. forecast usa somente a base curada;
4. KPIs usam curadoria e operacao;
5. reconciliacao verifica os joins;
6. cenarios usam a previsao congelada;
7. registro executivo resume as decisoes.

Nao executar o incremento antes do forecast estar congelado.

## 6. O que ainda falta

### Alta prioridade

- Incluir m3 e paletes na previsao ou modelar explicitamente a ausencia dessas dimensoes nos cenarios.
- Corrigir ou confirmar com o dono da fonte os 10 achados de qualidade.
- Validar a alocacao de veiculos com todos os limites de horas e capacidade, nao apenas kg.

### Media prioridade

- Criar comparacao formal do baseline contra uma referencia simples adicional.
- Detalhar KPIs por rota e galpao, alem dos totais.
- Implementar frescor das fontes e marcar dados operacionais antigos.
- Calcular intervalos de previsao somente depois de escolher metodo de calibracao.
- Adicionar custo por alternativa mutuamente exclusiva e economia potencial com premissas.

### Baixa prioridade

- Adicionar DuckDB ou Parquet se o volume justificar.
- Migrar validacao Node para Python apenas se houver beneficio claro.
- Melhorar a documentacao visual com diagrama de entidades e fluxo.

## 7. O que ainda nao deve ser feito

- Nao usar `avaliador_RESTRITO` ou holdout para ajustar o modelo.
- Nao carregar o incremental antes do congelamento da previsao.
- Nao somar carteira confirmada novamente a previsao manual total.
- Nao juntar custos brutos diretamente a pedidos.
- Nao declarar economia realizada.
- Nao apresentar capacidade em kg como capacidade valida em m3 ou paletes.
- Nao tratar ausencia de disponibilidade como indisponibilidade.
- Nao alterar os CSVs-base.

## 8. Criterio de conclusao do projeto

O projeto estara pronto para apresentacao quando:

- o pipeline rodar de forma repetivel;
- os testes automatizados forem executados e registrados;
- a base curada reconciliar pedidos, viagens, entregas e custos;
- o forecast tiver backtesting sem vazamento;
- a previsao congelada estiver preservada;
- os cenarios respeitarem capacidade multidimensional;
- as recomendacoes exibirem fato, hipotese, confianca e limitacao;
- o incremento for aplicado duas vezes sem duplicacao;
- a interface ou relatorio executivo permitir rastrear cada decisao ate sua fonte.

## 9. Proxima sequencia de trabalho

1. Fechar reconciliacao monetaria e regras de entrega.
2. Comparar indicadores antes e depois do incremento.
3. Construir a interface executiva sobre os arquivos de relatorio ja gerados.

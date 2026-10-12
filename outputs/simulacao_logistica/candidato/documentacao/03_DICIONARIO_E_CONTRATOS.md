# Dicionario e contratos de dados

O arquivo dicionario_dados.csv documenta cada campo. Tipos sao o contrato esperado: o bruto contem violacoes intencionais. Todos os dados sao inventados; nao provem de uma empresa ou fonte real.

## Formato e ingestao
CSV UTF-8 com BOM, separador ponto e virgula, decimal ponto, datas YYYY-MM-DD e timestamps ISO8601 com offset -03:00. Vazio representa desconhecido/nao aplicavel conforme contrato, nunca zero implicito. IDs sao texto e preservam zeros. BRL nominal, sem correcao monetaria ou analise tributaria. Nao ha dados pessoais reais.

## Graos e chaves
- **galpoes.csv**: Um galpao. Chave: `galpao_id`. Linhas brutas: 6.
- **rotas.csv**: Uma rota de distribuicao com retorno a base. Chave: `rota_id`. Linhas brutas: 12.
- **frota.csv**: Um veiculo proprio. Chave: `veiculo_id`. Linhas brutas: 48.
- **tarifas.csv**: Uma tarifa por rota e intervalo. Chave: `rota_id + vigencia_inicio`. Linhas brutas: 12.
- **calendario.csv**: Um dia do calendario interno. Chave: `data`. Linhas brutas: 642.
- **disponibilidade.csv**: Um veiculo por dia. Chave: `data + veiculo_id`. Linhas brutas: 30,815.
- **capacidade.csv**: Um galpao por dia. Chave: `data + galpao_id`. Linhas brutas: 3,852.
- **eventos_planejados.csv**: Um evento comercial conhecido. Chave: `evento_id`. Linhas brutas: 1.
- **pedidos.csv**: Uma versao de pedido; nao item SKU. Chave: `pedido_id + versao`. Linhas brutas: 44,012.
- **viagens.csv**: Um ciclo de distribuicao fechado, ida e volta. Chave: `viagem_id`. Linhas brutas: 8,517.
- **viagem_pedidos.csv**: Alocacao de um pedido numa viagem. Chave: `viagem_id + pedido_id`. Linhas brutas: 42,245.
- **entregas.csv**: Uma entrega final/parcial ou em transito por pedido. Chave: `entrega_id`. Linhas brutas: 42,245.
- **custos.csv**: Um componente de custo por viagem. Chave: `lancamento_id`. Linhas brutas: 18,295.
- **previsao_manual.csv**: Uma revisao de estimativa por rota/semana. Chave: `planilha_id`. Linhas brutas: 37.
- **aliases_rotas.csv**: Um alias aprovado. Chave: `alias`. Linhas brutas: 2.

## Relacionamentos e precedencia
Pedidos → rotas → galpoes. Viagens → rotas; viagem_pedidos liga pedidos e viagens. Neste recorte, cada pedido confirmado historico e embarcado uma vez; cancelados nao embarcam. Entregas se ligam a pedido E viagem, que devem concordar com a ponte. Custos sao N componentes por viagem: agregar antes de juntar a pedidos para evitar multiplicacao. Rateio opcional por peso embarcado, com diferencas de centavos reconciliadas por viagem. Nao confundir entrega parcial com nova demanda.

Frota → galpoes; disponibilidade por veiculo/dia deve cobrir toda a frota ativa (48 veiculos, sem admissoes/baixas). Ausencia de linha nao prova disponibilidade zero. O limite efetivo de capacidade diaria tem precedencia sobre o nominal; obra ja descontada. Limites de veiculo devem valer simultaneamente em kg, m3 e paletes. Nunca somar estas unidades.

Pedidos: CONFIRMADO ou CANCELADO. Disponibilidade: DISPONIVEL, MANUTENCAO ou FECHADO. Entregas: ENTREGUE, PARCIAL ou EM_TRANSITO. No historico, pedidos expedidos continuam CONFIRMADO; o estado de entrega pertence ao TMS. ENTREGUE exige peso integral; PARCIAL exige peso menor e positivo; EM_TRANSITO exige data e peso vazios. A entrega parcial e encerrada para este teste, sem nova tentativa. SLA por dia local inclusivo, sem calendario de feriados reais.

Nao existem feriados nacionais/estaduais no calendario sintetico: e um contrato de operacao, nao uma fonte legal. Domingo sem coleta/expedicao, embora uma entrega em transito possa terminar nesse dia. Um veiculo faz no maximo um ciclo por dia e retorna a base; nao ha realocacao entre galpoes. Horas do ciclo devem caber nas horas disponiveis. Nao modelamos jornada legal de motoristas, estoque em transito, roteirizacao de paradas ou cadeia fria. Nao extrapolar a solucao para operacao real sem revisar essas limitacoes.

## Tempo, fotografias e fontes
Corte de conhecimento: 2026-09-27 23:59:59 America/Sao_Paulo. Pedidos com coleta ate o corte sao historico; os de coleta posterior sao CARTEIRA CONFIRMADA conhecida, nao demanda realizada. O CSV de pedidos mistura esses dois usos propositalmente e exige filtros explicitos. Disponibilidade e capacidade futuras sao PLANOS conhecidos no corte. Previsao manual e sempre estimativa; nao deve entrar no alvo historico.

Base de pedidos e uma fotografia contendo v1; o incremental posterior contem atualizacoes e uma chegada tardia. Sua versao so vale a partir de atualizado_em. Lote entregue ao candidato e elegivel somente na fase posterior. Não ha CDC, exclusao fisica ou trilha completa de alteracoes antigas. Backtests com fotografias antigas de status sao aproximacoes: declarar essa limitacao. Custos historicos foram conhecidos no proprio dia no recorte, com uma violacao artificial de qualidade. Nenhuma entrega apos o corte aparece como realizada na base.

Previsao manual: resolver alias autorizado, converter unidade e escolher maior editado_em elegivel; desempate por versao; conflito residual exige excecao. A chave de negocio e semana + rota normalizada. Nao somar v1 e v2. Estimativa manual e DEMANDA TOTAL, ja incluindo carteira; nao adicionar carteira novamente. Em uma previsao estatistica total, carteira e piso conhecido ou componente explicitamente decomposto, nao parcela automaticamente somada.

## Custos e capacidade
Custos contem variavel proprio, frete-base terceiro, adicional emergencial e pedagio. Fixos da frota estao apenas no cadastro: custo fixo por dia corrido x veiculos. Valor-base regular nao inclui adicional nem pedagio. Tarifas futuras sao hipoteses contratuais do case, nao precos reais de mercado. Limite de dois terceiros regulares por rota/dia e restricao de planejamento futuro; realizado historico pode ter excedido contratos e deve ser descrito, nao reescrito. Emergencial sem teto contratual no exercicio, sujeito a disponibilidade real nao fornecida; nunca prometer que sera contratado.

Galpao limita expedicao, nao armazenagem. Se o plano viola kg OU m3, ha gargalo. Frota sobrando nao resolve automaticamente obra em doca. Cancelados nao entram em demanda liquida. Eventos planejados sao hipoteses: o uplift nao e pedido e nao deve ser aplicado outra vez a uma previsao que ja o incorpora.

# KPIs e limites de interpretacao

Todos os indicadores devem informar populacao, periodo, unidade, cobertura e corte. Quantidades historicas usam data_coleta; custos operacionais usam data_saida/competencia. Nao somar percentuais de rotas: recalcular pelos numeradores e denominadores.

| KPI | Definicao contratual | Limites |
|---|---|---|
| Demanda liquida | Soma de kg, m3 ou paletes de pedidos CONFIRMADO, ultima versao elegivel, por coleta/rota | Cancelado fora. Nao usar entregue como proxy de solicitado. Carteira futura separada. |
| Custo variavel operacional | Soma dos componentes de custos validos no periodo | Inclui pedagio, adicional e frete-base/variavel proprio; nao inclui fixos. |
| Custo total do recorte | Variavel + 420 BRL x 48 veiculos x dias corridos do periodo | Fixos persistem com ociosidade. Nao atribuir economia de fixo sem eliminacao real. |
| Custo por kg expedido | Variavel / peso embarcado das mesmas viagens elegiveis | Agregar custos antes da ponte; cobertura conjunta. Denominador zero = indisponivel. |
| Participacao emergencial | Viagens EMERGENCIAL / viagens totais | Contagem de viagens unicas, nao pedidos. |
| Adicional emergencial por kg | Soma ADICIONAL_EMERGENCIAL / kg expedido do mesmo escopo | Referencia para meta do piloto, nao comparar mix sem ajuste. |
| Ocupacao por peso / volume / paletes | Soma carga embarcada / soma capacidade das viagens, para cada unidade separada | Nao media simples de percentuais. Nao inclui frota que nao saiu. |
| Utilizacao da frota | Veiculos-dia proprios usados / veiculos-dia DISPONIVEL com horas > 0 | Uma viagem por dia no case; ausencias de disponibilidade afetam cobertura. |
| Ociosidade disponivel | Veiculos-dia disponiveis sem viagem / veiculos-dia disponiveis | Nao inclui manutencao; nao e custo evitavel automaticamente. |
| Entrega no prazo | Pedidos com data_entrega <= prometida / pedidos expedidos com prometida <= corte | Pendente vencido conta como falha; futura promessa excluida. Campo invalido deve gerar cobertura, nao sucesso. |
| OTIF | Pedidos da mesma coorte entregues no prazo E integralmente / pedidos expedidos com prometida <= corte | Integral: peso entregue >= solicitado com tolerancia 0.1 kg. Parcial falha, pendente vencido falha. |
| Backlog vencido | Pedidos expedidos com promessa < dia do corte e sem entrega encerrada | PARCIAL e encerrada neste case; nao reconduzir como backlog. |
| WAPE | Soma abs(previsao-real) / soma real | Por horizonte/rota e total, kg e m3 separados; denominador zero = indisponivel. |
| Vies | Soma(previsao-real) / soma real | Positivo = excesso. Informar tambem MAE em unidade fisica. |
| Cobertura de intervalo | Fracao de observacoes dentro do intervalo declarado | Nao nomear “95%” sem metodo/calibracao; avaliar separadamente largura e cobertura. |
| Sobrecarga do galpao | max(0, demanda prevista - cap efetiva) por unidade/dia | Peso e volume ambos limitam; nao compensar excesso diario com folga outro dia sem plano explicito. |
| Necessidade teorica de ciclos | max(ceil(kg/8000), ceil(m3/45), ceil(paletes/14)) | Limite inferior; cargas indivisiveis e roteamento podem exigir mais. Nao prova plano factivel. |
| Frescor | Instante de avaliacao - ultimo instante de fonte recebido | Hora do processamento nao prova atualizacao da origem. Registrar ambos se existentes. |
| Qualidade/cobertura | Registros e valor de negocio elegiveis vs esperados, por metrica | Registro rejeitado em volume pode continuar apto em peso se politica explicita. |

## Economia sem dupla contagem
Economia potencial = custo evitavel de referencia - custo incremental da alternativa - custo de implantacao/operacao alocado, com horizonte e hipoteses declarados. Trocar emergencial por proprio compara frete terceiro evitavel com variavel proprio + pedagio + demais incrementos; fixo existente nao desaparece. Trocar emergencial por regular so evita adicional se houver antecedencia e disponibilidade. Nao somar duas alternativas mutuamente exclusivas. Custo de oportunidade, remanejamento, multa e horas extras nao estao nos dados: cenarios precisam declarar essas lacunas.

Economia realizada exige custo observado contra contrafactual acordado, mesma demanda/mix, periodo piloto, custos de execucao e aceite financeiro. O holdout mede demanda, nao causalidade de economia. Compare semanas equivalentes e explique sazonalidade, mudancas de mix e servico. Nao prometer acuracia perfeita ou SLA de tempo real com arquivos em lote.

## Limites e alertas do case
Alerta de saturacao a partir de 90% do limite efetivo, critico acima de 100%; estes sao limiares acordados para simulacao, nao padroes universais. Dado diario com mais de 24 horas desde disponibilidade conhecida deve aparecer como atrasado, com ressalva para calendario de fontes. Planejamento de disponibilidade futura pode ter idade maior por ser um plano; mostrar emissao e vigencia separadamente, sem chama-lo de telemetria.

Estimativas de desempenho nao sao criterio absoluto de contratacao: exigimos baseline e avaliacao honesta. Um modelo mais complexo so se justifica se melhora as janelas temporais de modo consistente. No holdout final, nao se exige erro abaixo de uma porcentagem arbitraria. Demanda observada e parcialmente determinada pelo gerador sintetico e nao representa a variabilidade de toda logistica brasileira.

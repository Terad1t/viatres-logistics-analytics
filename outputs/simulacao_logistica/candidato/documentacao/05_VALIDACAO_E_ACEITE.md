# Cenarios de validacao e criterios de aceite

| Caso | Procedimento | Evidencia esperada |
|---|---|---|
| V01 Reexecucao | Carregar base duas vezes | Mesmas entidades, totais e resultados; duplicatas brutas rastreadas. |
| V02 Cardinalidade | Juntar custos, viagens e pedidos | Total de custos nao cresce com o numero de pedidos ou componentes. |
| V03 Qualidade | Procurar datas, dominios, FKs, negativos, nulos e duplicatas | Identificacao com arquivo/linha/chave, regra e tratamento; sem correcao inventada. |
| V04 Versoes manuais | Normalizar rota/unidade e selecionar revisao | Uma estimativa por rota/semana; t convertida; v2 substitui v1. |
| V05 Corte | Congelar em 27/09 23:59:59 | Carteira futura separada do realizado; lote posterior excluido; entregas futuras desconhecidas. |
| V06 Atualizacao | Aplicar incremental duas vezes em 28/09 08h | Uma entidade nova, uma entidade atualizada, nenhum aumento na segunda aplicacao; snapshots preservados. |
| V07 Disponibilidade | Cruzar frota x dias futuros | Lacuna nao vira disponibilidade nem zero silencioso; cobertura e intervalo de capacidade. |
| V08 Restricoes | Obra de G01, campanha de R05, manutencao de G03 | Alertas de capacidade por dia/unidade e limite de frota; nao usar caminhao de outra base sem autorizacao. |
| V09 Sem demanda | Incluir domingo e divisores nulos | Demanda contratual zero; WAPE/custo unitario indisponivel se denominador zero, sem erro mascarado. |
| V10 Servico | Parcial, transito, atrasada e prazo futuro | OTIF e pontualidade seguem coorte de promessa; pendente vencido nao desaparece. |
| V11 Stress | +20% demanda e perda de um veiculo/base em 29/09 | Deficits e custos recalculados; restricoes continuam respeitadas. |
| V12 Previsao | Quatro janelas temporais e holdout congelado | Baseline, WAPE, vies, MAE, dados elegiveis e explicacao da incerteza; sem vazamento. |
| V13 Economia | Comparar alternativas mutuamente exclusivas | Fixos nao evitaveis preservados, adicional sem dupla contagem, hipoteses e faixas. |
| V14 Auditabilidade | Escolher um alerta e rastrear dados | Fonte, chave, corte, regra, calculo, acao e responsavel sugerido recuperaveis. |

## Aceite minimo obrigatorio
Execucao reproduzivel; bruto preservado; chaves e graos corretos; duplicatas sem efeito nos totais; invalidos visiveis com tratamento; corte temporal respeitado; lote idempotente; restricoes de capacidade simultaneas; pelo menos uma previsao baseline avaliada; visao que liga gargalo a acao/custo; limites explicitos. Totais devem reconciliar a populacao que o candidato declarou elegivel, nao uma base “ideal” desconhecida.

Tolerancias: contagens/IDs/datas exatos; monetario por lancamento 0.01 BRL, total 0.05 BRL por arredondamento demonstrado; kg 0.1, m3 0.01 por registro; taxas 0.1 ponto percentual por arredondamento. Divergencias de politica de quarentena exigem ponte quantitativa. Valor impossivel nao precisa ser recuperado. Avaliar previsao por evidencia, nao por reproduzir o gerador.

## Rubrica (100 pontos)
- Pipeline, reprocessamento, incremental e rastreabilidade: 25.
- Qualidade, contrato, reconciliacao e juncoes: 20.
- Analytics de custo, servico e capacidade: 20.
- Previsao, baseline, backtest, incerteza e corte: 20.
- Clareza de decisao, execucao e limites: 15.

Referencia de aprovacao: >=75 e todos os criterios minimos. Pontuar cada grupo como ausente (0%), parcial (50%), completo com evidencia (100%), admitindo fracao justificada. Vazamento temporal material, custo multiplicado por join, capacidade fisicamente impossivel apresentada como factivel ou economia garantida sem evidencia impedem aceite ate correcao. Uma tecnologia especifica, dashboard bonito ou modelo complexo nao garantem pontos.

# Material reservado ao avaliador

Nao entregar esta pasta nem o ZIP completo ao candidato. Enviar somente candidato.zip. Todos os dados sao sinteticos, seed 27102026, versao do pacote 1.0. O gerador nao e fornecido ao candidato; nao ha pipeline pronto ou solucao de referencia implementada.

## Aplicacao
1. Entregue briefing, contratos, criterios e base; mantenha o incremental fechado ate congelar previsao.
2. Registre o hash da entrega/previsao, data_corte e momento de recebimento.
3. Libere fase incremental e aplique duas vezes. O pedido P0043909 passa de CONFIRMADO v1 para CANCELADO v2; P9000001 e novo e tardio. A segunda aplicacao nao altera totais. Carteira confirmada cai 1316.1 kg; historico confirmado sobe 507.6 kg. O alvo holdout permanece fotografia original para a previsao original.
4. Compare a previsao congelada com holdout/alvo_diario.csv, que cobre 84 combinacoes (7 dias x 12 rotas), incluindo domingos zerados. WAPE/vies por kg e m3, agregados e por rota; nao ajustar modelo depois da abertura.
5. Faça entrevista pedindo explicacao de uma rejeicao, uma juncao, um alerta e um custo evitavel. Aplique a rubrica publica e registre justificativas.

## Gabarito de qualidade
manifesto_anomalias.csv lista 17 ocorrencias, incluindo uma revisao manual legitima e dois campos do mesmo caso de unidade. Nao interpretar 17 como numero de linhas a excluir. A linha informada e a linha fisica CSV incluindo cabecalho; ausencia e identificada por chave, sem numero de linha. Referencia_limpa registra a verdade antes da injecao, nao uma saida de limpeza exigida. Ela nao inclui a revisao manual v2 legitima nem o incremental. Um candidato nao consegue inferir o peso original de um negativo ou a data originalmente invalida: quarentena justificada e a resposta adequada.

Controles_referencia.csv traz contagens e totais independentes da base antes das falhas; use para conferir identidade e calcular efeito das exclusoes, nunca para exigir imputacao invisivel. Normalizacao de status, aliases, unidade e duplicata exata sao recuperaveis. v2 manual deve prevalecer apos normalizacao; planilha M037 substitui M025 para R01 em 28/09. A conversao de toneladas preserva o valor com tolerancia 0.1 kg.

## Evidencias esperadas de negocio
G01 tem obra de 28 a 30/09: 12.600 kg e 67,5 m3/dia, 30% do nominal. O candidato deve identificar a reducao mesmo que seu metodo de previsao nao ultrapasse todos os limites. Terceirizacao sozinha nao amplia a doca. R05 tem campanha +35% como hipotese conhecida, sem garantir exatamente esse crescimento. G03 tem manutencao adicional planejada em parte da frota. V040 em 29/09 nao tem linha de disponibilidade: o total de capacidade precisa expor a incerteza. Ha frota propria ociosa coexistindo com frete terceiro por decisao manual; isso sugere investigacao, nao prova automaticamente economia capturavel.

## Como pontuar com equidade
Qualidade do raciocinio e evidencias valem mais que acertar o gerador. Aceite tecnologias distintas, relatorio simples ou dashboard e politicas de quarentena diferentes com ponte quantitativa. Exija os criterios minimos publicos. Nao use rendimento em um unico holdout como unico criterio de contratacao. Nao exigir Kafka, MLOps, otimizador de rotas ou deploy, ausentes do escopo.

## O que a simulacao nao valida
Capacidade de escala de producao, integracao CDC, confiabilidade de APIs, latencia em tempo real, restricoes legais de motoristas, precos reais, tributos, estoque, seguranca operacional ou economia causal. O holdout tem apenas demanda e nao contem custos/entregas futuros realizados.

## Casos numericos isolados
Use microcenarios_numericos.csv para verificar formulas e limites com entradas pequenas, independentes dos totais do gerador. Sao gabaritos de teste, nao implementacoes.

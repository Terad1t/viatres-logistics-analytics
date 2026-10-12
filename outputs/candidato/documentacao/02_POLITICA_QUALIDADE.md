# Politica de tratamento da qualidade

Esta politica define como os achados da Etapa 2 entram ou nao nas tabelas curadas. O bruto permanece sempre preservado.

## Principios

- Nao corrigir valores por adivinhacao.
- Nao apagar registros invalidos.
- Manter o registro original na quarentena.
- Informar a populacao elegivel de cada metrica.
- Permitir que uma metrica continue usando um registro somente quando a unidade necessaria estiver valida.
- Bloquear joins que possam multiplicar custos ou pedidos.

## Regras atuais

| Achado | Tratamento na camada curada | Motivo |
|---|---|---|
| Chave duplicada de pedido | Excluir o grupo duplicado da selecao automatica | Nao e seguro escolher uma versao por adivinhacao |
| Pedido com rota inexistente | Excluir da demanda curada e da ponte analitica | Nao e possivel atribuir galpao ou rota |
| Pedido com campo obrigatorio ausente | Excluir de fatos multidimensionais; manter na quarentena | Evita inventar volume, peso ou outra medida |
| Medida fisica negativa | Excluir da demanda curada e manter na quarentena | Peso, volume e paletes nao podem ser negativos |
| Status fora do dominio | Excluir da demanda curada | Nao e seguro classificar como confirmado ou cancelado |
| Chave duplicada de custo | Excluir os lancamentos duplicados da soma | Evita contar o mesmo custo duas vezes |
| Custo sem viagem existente | Excluir do custo por viagem | Nao e possivel atribuir rota, data ou modalidade |
| Unidade `t` na previsao | Aceitar e converter para kg por `1 t = 1000 kg` | Regra explicita no dicionario de dados |
| Alias autorizado de rota | Normalizar preservando o valor original | Regra aprovada em `aliases_rotas.csv` |
| Viagem terceirizada sem veiculo | Aceitar | `veiculo_id` e nulo condicionalmente para terceiros |
| Entrega em transito sem data/peso | Aceitar | E o contrato esperado para esse status |

## Impacto

As exclusoes devem ser quantificadas antes de calcular cada KPI. Um registro excluido por volume ausente pode nao afetar uma metrica de kg, mas afeta ocupacao por m3 e qualquer KPI que dependa da cobertura completa.

A previsao manual convertida para kg continua sendo demanda total. A carteira confirmada nao pode ser somada novamente a ela.

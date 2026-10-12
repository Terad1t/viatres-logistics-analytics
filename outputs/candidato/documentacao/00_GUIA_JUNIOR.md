# Guia introdutorio do projeto ViaTres Logistica

Este documento explica o projeto para quem esta começando em engenharia de dados e analytics.

## 1. O que estamos construindo

A ViaTres e uma empresa ficticia de distribuicao B2B. Ela possui galpoes, caminhoes, rotas, pedidos, viagens, entregas e custos.

A diretoria quer responder perguntas praticas:

- Quanto de carga ja esta confirmado?
- Quanto ainda e apenas previsao?
- Qual galpao, rota ou dia pode ficar sobrecarregado?
- Vale usar caminhao proprio, frete regular, frete emergencial ou negociar uma janela?
- Qual e o custo de cada alternativa?
- Existe risco de atraso ou piora no OTIF?

O objetivo nao e criar um grafico bonito primeiro. O objetivo e construir uma base confiavel para que qualquer indicador possa ser explicado e reproduzido.

## 2. O principio mais importante

Antes de calcular qualquer KPI, precisamos saber:

1. qual e a fonte do dado;
2. qual e a granularidade da tabela;
3. qual e a chave que identifica cada registro;
4. qual e a data em que o registro podia ser conhecido;
5. quais regras de negocio devem ser aplicadas;
6. quais registros sao validos, invalidos ou desconhecidos.

Um resultado numerico sem essas respostas pode parecer correto e ainda assim estar errado.

## 3. Pastas principais

### `outputs/candidato/`

E a entrega que sera usada para desenvolver a solucao. Contem os CSVs, a documentacao e os manifestos do pacote candidato.

### `outputs/candidato/dados/base/`

Contem as fontes historicas e os cadastros principais. Estes CSVs sao a fonte autoritativa do exercicio.

Nao devemos editar esses arquivos. O bruto precisa permanecer preservado para auditoria e reprocessamento.

### `outputs/candidato/dados/incremental/`

Contem dados que chegaram depois do corte inicial. O lote deve ser aplicado somente depois de congelarmos a previsao original.

O arquivo atual contem:

- uma nova versao de um pedido existente;
- um pedido recebido com atraso de ingestao.

O mesmo lote precisa poder ser aplicado duas vezes sem duplicar resultados.

### `outputs/candidato/documentacao/`

Contem o contexto empresarial, os contratos dos dados, os KPIs, os limites e os criterios de aceite.

O arquivo `00_GUIA_JUNIOR.md` e este guia.

### `outputs/pacote_completo_logistica/`

E uma copia completa do pacote, com materiais adicionais de avaliacao. Os CSVs-base foram comparados por SHA-256 e sao iguais aos do pacote candidato.

### `outputs/simulacao_logistica/`

E outra copia preparada para a simulacao incremental. Tambem possui os mesmos CSVs-base.

### `avaliador_RESTRITO/`

Contem referencias, controles e holdouts usados para avaliar uma solucao. Nao deve ser usada pelo pipeline candidato, nem para treinar ou ajustar o forecast.

Em especial, nao devemos abrir ou usar o holdout para tomar decisoes antes da previsao congelada.

### `work/`

Contem scripts e arquivos auxiliares usados para montar ou verificar o pacote original, como scripts de geracao, checks e previews. Nao e a camada analitica que vamos entregar.

## 4. O que cada arquivo de dados representa

### Cadastros e regras operacionais

- `galpoes.csv`: um registro por galpao. Informa cidade, estado, capacidade de expedicao e docas.
- `rotas.csv`: uma rota de distribuicao com retorno a base. Informa distancia, duracao, SLA e limites de carga.
- `frota.csv`: um registro por veiculo proprio. Informa o galpao-base e limites de kg, m3 e paletes.
- `tarifas.csv`: tarifa regular por rota e periodo de vigencia. Tambem informa adicional emergencial, pedagio e limite regular.
- `calendario.csv`: um registro por dia do calendario operacional. Ajuda a tratar domingos e fatores da operacao.
- `disponibilidade.csv`: status e horas disponiveis de cada veiculo por dia. Linha ausente significa desconhecido, nao automaticamente disponivel ou indisponivel.
- `capacidade.csv`: capacidade diaria de cada galpao. A capacidade efetiva informada tem prioridade sobre a capacidade nominal.
- `eventos_planejados.csv`: eventos comerciais conhecidos que podem alterar a demanda. O impacto do evento nao deve ser somado novamente se ja estiver incluido na previsao.
- `aliases_rotas.csv`: mapeamentos aprovados para normalizar nomes de rotas, preservando o valor original.

### Operacao

- `pedidos.csv`: varias versoes de pedidos. Cada pedido pode aparecer mais de uma vez; precisamos selecionar a versao elegivel mais recente no corte.
- `viagens.csv`: uma linha por viagem ou ciclo de distribuicao. Indica rota, data, modalidade e, quando aplicavel, veiculo.
- `viagem_pedidos.csv`: ponte entre viagens e pedidos. E a tabela usada para saber quais pedidos foram embarcados em cada viagem.
- `entregas.csv`: resultado da entrega de um pedido. Pode estar entregue, parcial ou em transito.
- `custos.csv`: lancamentos de componentes de custo por viagem. Uma viagem possui varios lancamentos, portanto os custos devem ser agregados antes de juntar com pedidos.
- `previsao_manual.csv`: revisoes de previsao por rota e semana. A previsao representa a demanda total esperada e ja inclui a carteira confirmada.

### Documentacao auxiliar

- `dicionario_dados.csv`: descreve campos, tipos, dominios, chaves e regras esperadas.
- `MANIFESTO_SHA256.csv`: permite conferir se um arquivo foi alterado.
- `LEIA_PRIMEIRO.md`: explica a ordem de leitura e as regras basicas do pacote.

## 5. Conceitos que costumam confundir

### Granularidade

Granularidade e o que uma linha representa.

Exemplo: uma linha de `custos.csv` representa um lancamento de custo, nao necessariamente uma viagem inteira. Uma viagem pode possuir varios lancamentos.

Se juntarmos custos diretamente a varios pedidos da mesma viagem, o mesmo custo sera repetido. Por isso primeiro agregamos custos por `viagem_id` e componente.

### Versao de pedido

Um pedido pode ter versoes antigas e novas. Nao podemos somar todas as versoes. Devemos escolher a versao mais recente que era elegivel no corte de conhecimento.

### Corte temporal

O corte inicial e `2026-09-27 23:59:59`, no fuso `America/Sao_Paulo`.

- Coleta ate o corte: pode compor o historico.
- Coleta depois do corte: e carteira futura.
- Dados do lote incremental: nao podem influenciar a previsao original.

### Demanda realizada, carteira e previsao

Sao coisas diferentes:

- demanda realizada: carga historica efetivamente expedida;
- carteira confirmada: pedidos futuros ja conhecidos;
- previsao: estimativa da demanda total esperada.

Nao devemos somar carteira novamente a uma previsao manual que ja a inclui.

### Capacidade multidimensional

Kg, m3 e paletes sao limites diferentes. Nao devemos soma-los nem olhar apenas para um deles.

Uma operacao tem gargalo se ultrapassar qualquer dimensao relevante. Mesmo uma estimativa de ciclos baseada em kg, m3 e paletes ainda precisa respeitar base do veiculo, disponibilidade, horas, galpao e retorno.

### Custo fixo e custo evitavel

O custo fixo diario dos veiculos continua existindo mesmo quando um veiculo fica ocioso. Portanto, retirar uma viagem propria nao significa automaticamente economizar todo o custo fixo daquele veiculo.

Toda economia sera apresentada como potencial ou estimada ate existir um contrafactual validado com a area financeira.

## 6. Etapas do trabalho

### Etapa 1 - Inventario e entendimento

Confirmar os arquivos recebidos, ler os contratos, conhecer schemas, chaves, datas, dominios e relacionamentos.

Resultado esperado: diagnostico inicial e lista de riscos.

### Etapa 2 - Contratos e qualidade

Criar regras para tipos, chaves, valores obrigatorios, dominios, datas, duplicidades e referencias.

Registros invalidos nao devem desaparecer. Devem ser preservados e encaminhados para quarentena com motivo e impacto.

### Etapa 3 - Ingestao e modelo curado

Ler os CSVs sem modificar o bruto, normalizar aliases, selecionar versoes, validar joins e criar tabelas analiticas com granularidade explicita.

O pipeline deve ser idempotente: repetir a mesma execucao deve produzir o mesmo resultado.

### Etapa 4 - KPIs

Calcular demanda, custos, capacidade e servico com denominadores corretos. Cada KPI deve indicar fonte, corte, filtros e limitacoes.

### Etapa 5 - Forecast

Comecar com um baseline simples e explicavel. Avaliar quatro janelas temporais sem usar dados futuros. Depois gerar e congelar a previsao de `2026-09-28` a `2026-10-04`.

### Etapa 6 - Cenarios

Comparar o cenario-base, aumento de 20% na demanda e perda de um veiculo comprovadamente disponivel por galpao em `2026-09-29`.

Cada alternativa deve mostrar viabilidade, capacidade, custo incremental, risco, premissas e confianca.

### Etapa 7 - Interface e testes finais

Montar uma visao executiva somente depois que os dados e KPIs estiverem validados. Executar testes de qualidade, reconciliação, idempotencia, forecast e cenarios.

### Etapa 8 - Incremental

Avancar o relogio para `2026-09-28 08:00`, aplicar o lote, preservar a previsao congelada e demonstrar que reaplicar o lote nao duplica dados.

## 7. Proximo passo pratico

O proximo passo e implementar a camada de contratos e qualidade:

1. ler cada CSV preservando IDs como texto;
2. gerar inventario de arquivo, tamanho, colunas e contagem;
3. validar chaves e duplicidades;
4. validar dominios, nulos, datas e referencias;
5. gerar um relatorio de qualidade;
6. separar registros invalidos em quarentena sem apagar o original.

Ainda nao devemos treinar um modelo, processar o incremento ou construir o dashboard. Primeiro precisamos provar que a base esta sendo interpretada corretamente.

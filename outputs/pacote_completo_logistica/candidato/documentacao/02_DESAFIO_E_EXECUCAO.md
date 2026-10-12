# Desafio e guia de execucao

## Escopo e tempo
Exercicio para desenvolvedor de pipelines e analytics, nao para construir um ERP. Sugestao de avaliacao: 12–16 horas de trabalho focado, com prazo de entrega combinado de 5 dias e conversa de 45 minutos. Se o tempo acabar, entregar nucleo correto e registrar extensoes. Tecnologia livre, execucao local; sem conta paga, servico cloud, API real ou credenciais. Este pacote nao implementa o sistema.

## Sequencia
1. Leia briefing e contratos. Inspecione os CSVs; registre suposicoes, perguntas e graos antes de juntar tabelas. O XLSX e uma copia de apoio das planilhas manuais e cadastros, nao uma segunda fonte para uniao. Historico volumoso esta completo em CSV.
2. Construa ingestao repetivel, preservando bruto e origem (arquivo, linha, instante/lote). Defina chaves, tipos, regras de normalizacao, quarentena e selecao de versoes. Publique contagens de entrada, aceitas, deduplicadas e rejeitadas sem perder rastreabilidade.
3. Modele demanda por data de coleta/rota em kg, m3 e paletes; separe pedidos cancelados, carteira futura e historico. Modele custo e servico sem multiplicacao nas juncoes. Inclua dias conhecidos sem demanda, distinguindo-os de ausencia de fonte.
4. Produza ao menos uma referencia simples de previsao para a semana seguinte, e compare com as estimativas manuais onde ha cobertura. Use apenas informacoes elegiveis no corte. Preveja kg e m3; trate paletes e restricoes na avaliacao da frota. Modelo sofisticado nao e obrigatorio.
5. Faca backtest temporal em quatro janelas semanais: treino ate 30/08 e teste 31/08–06/09; ate 06/09 e teste 07–13/09; ate 13/09 e teste 14–20/09; ate 20/09 e teste 21–27/09. Dados futuros de cada janela nao podem servir para ajuste, limpeza aprendida, selecao de parametros ou calculo de intervalos. Estimativas manuais existem para apenas duas dessas semanas; nao inventar as anteriores. A campanha so era conhecida em 24/09.
6. Congele previsao final com gerado_em, data_corte, horizonte, rota, data, estimativa, unidade, metodo, limite inferior/superior se disponiveis e justificativa da incerteza. Entregue tabela diaria e consolidacao semanal; domingo zero contratual. Informe como evita somar carteira e demanda total duas vezes. Comente rotas de baixo volume e mudancas de regime.
7. Cruze demanda com capacidade simultanea em peso/volume, frota por base, horas, paletes, limites de terceiros e antecedencia de reserva. Mostre alertas acionaveis, responsavel sugerido e custo incremental. Nao precisa otimizar rotas ou implementar solver. Uma heuristica transparente com limites declarados e suficiente.
8. Apresente uma visao para o CEO, em dashboard local OU relatorio navegavel/tabelas claras, que permita rastrear decisao ate fonte, cobertura e data da extracao. Separe realizado, carteira, previsao e cenario. Compare ao menos cenario base, +20% de demanda e perda de um veiculo disponivel por galpao em 29/09.
9. Somente depois de congelar a previsao, avance o relogio para 28/09 08h, aplique o incremental e reaplique o mesmo lote. Demonstre atualizacao por versao, chegada tardia, ausencia de duplicacao e preservacao da previsao anterior.
10. Execute cenarios de validacao e entregue evidencias. O avaliador libera resultados futuros apenas apos congelamento. Nao refazer a previsao apos ver o holdout para melhorar nota.

## Entregaveis do candidato
- Codigo e dependencias fixadas, comando unico ou passos curtos de execucao do zero e de reprocessamento.
- Modelo de dados e decisoes de limpeza; relatorio de qualidade por fonte e metrica, com registros afetados e efeito nos totais.
- Tabelas curadas, previsao congelada e relatorio de backtest; baseline, erro, vies e limites.
- Visao executiva com 3–5 acoes priorizadas, faixa de custo/economia potencial e motivos.
- Testes de consistencia, repeticao de lote, corte temporal e cenarios; evidencias e limitacoes.
- README com recursos usados e tempos medidos na maquina descrita. Nenhum limite arbitrario de latencia e exigido.

## Regras operacionais do teste
Fixe timezone America/Sao_Paulo e corte fornecido; nao use o dia atual do computador. Custos e capacidade possuem unidades distintas. Sem acesso a resultados reservados. Nao corrija um valor impossivel inventando seu valor original. A avaliacao aceita quarentena e cobertura explicita; “limpar tudo para bater o gabarito” nao e objetivo.

O arquivo incremental e deliberadamente enviado junto, mas nao e elegivel na fase inicial. A avaliacao final precisa preservar esse isolamento logico. Para sessao supervisionada, o avaliador pode fornecer a pasta incremental somente na etapa 9.

## Perguntas que esperamos levantar
Qual decisao tem prioridade e quem aprova terceirizacao? Demanda significa solicitado, confirmado, coletado ou entregue? Ha cancelamentos posteriores ou pedidos sem coleta? Qual e o horario de fechamento por galpao? Os limites sao de doca, equipe, peso, volume ou estoque? Caminhao pode operar fora da base? Quem verifica disponibilidade de motoristas e restricoes legais? Como a tarifa varia por carga/peso e qual o custo de adiar? Existem restricoes por cliente, devolucoes e reentregas? Que latencia de fonte e aceitavel? Quem e dono do ERP/TMS/financeiro? Como medir horas economizadas e validar gasto evitado? Qual historico de snapshots existe? Como tratar demanda perdida que nunca virou pedido?

Nao dependa de resposta para seguir: registre suposicoes reversiveis do case; destaque quais precisam ser confirmadas antes de producao. ERP/TMS ficticios sao representados por pedidos e entregas/viagens; financeiro por custos; equipes por planilha manual. Atualizacao de lote diario e o alvo do prototipo; integracao continua fica fora do escopo.

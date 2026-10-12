# Relatorio de qualidade

Este diretorio e gerado pelo validador de contratos da Etapa 2.

## Como executar

Na raiz do projeto:

```powershell
node src\quality\validate_contracts.mjs
```

O comando le somente `outputs/candidato/dados/base/`. Os arquivos de origem nao sao modificados.

## Saidas

- `inventory.csv`: um resumo por arquivo, com bytes, registros, quantidade de colunas e cabecalho.
- `quality_findings.csv`: um achado por regra e registro, com arquivo, linha, campo, severidade e mensagem.
- `quality_summary.json`: contagem da execucao, corte temporal e regras encontradas.
- `quarantine/`: registros que possuem achados, preservados com os campos originais e colunas `_rule`, `_field` e `_message`.

A quarentena e uma copia de trabalho para analise. Ela nao substitui nem altera o bruto.

## Regras atuais

O validador verifica:

- campos obrigatorios;
- chaves duplicadas;
- datas ISO e corte inicial;
- dominios documentados;
- valores numericos;
- referencias entre tabelas;
- contrato condicional de entregas.

A unidade `t` em `previsao_manual.csv` e valida pelo contrato. A conversao para kg sera aplicada na etapa de transformacao, usando `1 t = 1000 kg` conforme o dicionario.

## Resultado inicial

A execucao validou 15 arquivos e 190.741 registros. Foram encontrados 8 achados em 2 arquivos de quarentena:

- `custos.csv`: chave duplicada e referencia para viagem inexistente;
- `pedidos.csv`: chave duplicada, campo `volume_m3` vazio, status com espacos e rota inexistente.

Esses registros nao devem ser corrigidos por adivinhacao. A politica de inclusao ou exclusao deve ser documentada antes da camada curada.

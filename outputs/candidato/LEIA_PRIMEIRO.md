# Simulacao ViaTres Logistica

Comece por documentacao/01_BRIEFING_CEO.md e 02_DESAFIO_E_EXECUCAO.md. Leia os contratos, KPIs e aceite antes de implementar. Todos os dados sao ficticios e foram criados para avaliacao tecnica.

Base: 01/01/2025 a 27/09/2026. Corte de conhecimento: 27/09/2026 23:59:59, America/Sao_Paulo. Horizonte: 28/09 a 04/10/2026. O relogio do exercicio e fixo, independente da data atual.

- dados/base/: fontes CSV completas. Nao juntar XLSX como uma segunda fonte.
- planilhas_operacionais.xlsx: copia das previsoes manuais, cadastros e tarifas para inspecao humana; nao contem todo o historico volumoso.
- dados/incremental/: lote posterior, liberado apenas depois de congelar previsao.
- documentacao/: briefing, guia, dicionario por campo, KPIs, cenarios e rubrica.

Falhas de qualidade fazem parte do desafio. Nao existe sistema pronto neste pacote. O candidato deve criar a solucao; os documentos estabelecem escopo e evidencias esperadas. CSVs sao a fonte autoritativa. O XLSX preserva erros manuais, sem marca-los individualmente.

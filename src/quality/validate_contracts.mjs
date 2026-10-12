import fs from 'node:fs';
import path from 'node:path';

const projectRoot = path.resolve(import.meta.dirname, '..', '..');
const sourceDir = path.join(projectRoot, 'outputs', 'candidato', 'dados', 'base');
const reportDir = path.join(projectRoot, 'reports', 'quality');
const quarantineDir = path.join(reportDir, 'quarantine');
const cutoff = '2026-09-27T23:59:59-03:00';

const schemas = {
  'aliases_rotas.csv': { key: ['alias'], required: ['alias', 'rota_id'] },
  'calendario.csv': { key: ['data'], required: ['data', 'dia_semana', 'fator_operacao', 'observacao'], dates: ['data'] },
  'capacidade.csv': { key: ['data', 'galpao_id'], required: ['data', 'galpao_id', 'cap_kg_dia', 'cap_m3_dia', 'natureza', 'motivo', 'registrado_em'], dates: ['data', 'registrado_em'], domains: { natureza: ['REALIZADO', 'PLANEJADO'] } },
  'custos.csv': { key: ['lancamento_id'], required: ['lancamento_id', 'viagem_id', 'competencia', 'componente', 'valor_brl', 'registrado_em'], dates: ['competencia', 'registrado_em'], domains: { componente: ['PEDAGIO', 'VARIAVEL_PROPRIO', 'FRETE_BASE', 'ADICIONAL_EMERGENCIAL'] } },
  'disponibilidade.csv': { key: ['data', 'veiculo_id'], required: ['data', 'veiculo_id', 'status', 'horas_disponiveis', 'natureza', 'registrado_em'], dates: ['data', 'registrado_em'], domains: { status: ['DISPONIVEL', 'MANUTENCAO', 'FECHADO'], natureza: ['REALIZADO', 'PLANEJADO'] } },
  'entregas.csv': { key: ['entrega_id'], required: ['entrega_id', 'pedido_id', 'viagem_id', 'status', 'registrado_em'], dates: ['data_entrega', 'registrado_em'], domains: { status: ['ENTREGUE', 'PARCIAL', 'EM_TRANSITO'] } },
  'eventos_planejados.csv': { key: ['evento_id'], required: ['evento_id', 'rota_id', 'inicio', 'fim', 'impacto_demanda_pct', 'registrado_em', 'descricao'], dates: ['inicio', 'fim', 'registrado_em'] },
  'frota.csv': { key: ['veiculo_id'], required: ['veiculo_id', 'galpao_base_id', 'tipo', 'cap_kg', 'cap_m3', 'cap_paletes', 'custo_fixo_dia_brl', 'custo_variavel_km_brl'] },
  'galpoes.csv': { key: ['galpao_id'], required: ['galpao_id', 'uf', 'cidade', 'capacidade_expedicao_kg_dia', 'capacidade_expedicao_m3_dia', 'docas'] },
  'pedidos.csv': { key: ['pedido_id', 'versao'], required: ['pedido_id', 'versao', 'criado_em', 'atualizado_em', 'rota_id', 'cliente_id', 'data_coleta', 'data_prometida', 'peso_kg', 'volume_m3', 'paletes', 'status'], dates: ['criado_em', 'atualizado_em', 'data_coleta', 'data_prometida'], domains: { status: ['CONFIRMADO', 'CANCELADO'] } },
  'previsao_manual.csv': { key: ['planilha_id'], required: ['planilha_id', 'semana_inicio', 'rota_digitada', 'demanda_digitada', 'unidade', 'versao', 'editado_em', 'responsavel', 'observacao'], dates: ['semana_inicio', 'editado_em'], domains: { unidade: ['kg', 't'] } },
  'rotas.csv': { key: ['rota_id'], required: ['rota_id', 'galpao_origem_id', 'uf_destino', 'cidade_destino', 'km_ciclo', 'horas_ciclo', 'sla_dias', 'cap_kg', 'cap_m3', 'cap_paletes'] },
  'tarifas.csv': { key: ['rota_id', 'vigencia_inicio'], required: ['rota_id', 'vigencia_inicio', 'vigencia_fim', 'frete_regular_ciclo_brl', 'adicional_emergencial_pct', 'pedagio_ciclo_brl', 'limite_regular_viagens_dia', 'antecedencia_regular_h'], dates: ['vigencia_inicio', 'vigencia_fim'] },
  'viagem_pedidos.csv': { key: ['viagem_id', 'pedido_id'], required: ['viagem_id', 'pedido_id', 'peso_embarcado_kg', 'volume_embarcado_m3', 'paletes_embarcados'] },
  'viagens.csv': { key: ['viagem_id'], required: ['viagem_id', 'rota_id', 'data_saida', 'modalidade', 'cap_kg', 'cap_m3', 'cap_paletes', 'km_ciclo', 'horas_ciclo'], dates: ['data_saida'], domains: { modalidade: ['PROPRIO', 'REGULAR', 'EMERGENCIAL'] } }
};

function parseCsv(text) {
  const rows = [];
  let row = [], field = '', quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (char === '"' && quoted && next === '"') { field += '"'; i += 1; continue; }
    if (char === '"') { quoted = !quoted; continue; }
    if (char === ';' && !quoted) { row.push(field); field = ''; continue; }
    if ((char === '\n' || char === '\r') && !quoted) {
      if (char === '\r' && next === '\n') i += 1;
      row.push(field); field = '';
      if (row.some(value => value !== '')) rows.push(row);
      row = [];
      continue;
    }
    field += char;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  const headers = rows.shift().map(value => value.replace(/^\uFEFF/, ''));
  return rows.map((values, index) => ({
    lineNumber: index + 2,
    values: Object.fromEntries(headers.map((header, position) => [header, values[position] ?? '']))
  }));
}

function csvEscape(value) {
  const text = String(value ?? '');
  return /[;"\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function writeCsv(filePath, rows, columns) {
  const content = [columns.join(';'), ...rows.map(row => columns.map(column => csvEscape(row[column])).join(';'))].join('\n') + '\n';
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, 'utf8');
}

function isDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(value)) return false;
  const [year, month, day] = value.slice(0, 10).split('-').map(Number);
  const calendarDate = new Date(Date.UTC(year, month - 1, day));
  return calendarDate.getUTCFullYear() === year && calendarDate.getUTCMonth() === month - 1 && calendarDate.getUTCDate() === day && !Number.isNaN(Date.parse(value));
}

function isNumeric(value) {
  return value !== '' && Number.isFinite(Number(value));
}

function addFinding(findings, file, row, rule, severity, field, message) {
  findings.push({ file, line_number: row?.lineNumber ?? '', rule, severity, field, message, key: row ? Object.values(row.values).slice(0, 2).join('|') : '' });
}

function duplicateFindings(file, rows, key, findings) {
  const groups = new Map();
  for (const row of rows) {
    const value = key.map(field => row.values[field]).join('|');
    if (!groups.has(value)) groups.set(value, []);
    groups.get(value).push(row);
  }
  for (const [value, group] of groups) {
    if (group.length > 1) {
      for (const row of group) addFinding(findings, file, row, 'DUPLICATE_KEY', 'ERROR', key.join('+'), `Chave duplicada: ${value}`);
    }
  }
}

const findings = [];
const quarantine = new Map();
const inventory = [];
const tables = new Map();

for (const file of Object.keys(schemas).sort()) {
  const filePath = path.join(sourceDir, file);
  const raw = fs.readFileSync(filePath, 'utf8');
  const rows = parseCsv(raw);
  const headers = rows.length ? Object.keys(rows[0].values) : [];
  const schema = schemas[file];
  tables.set(file, rows);
  inventory.push({ file, bytes: fs.statSync(filePath).size, records: rows.length, columns: headers.length, header: headers.join('|') });
  duplicateFindings(file, rows, schema.key, findings);
  for (const row of rows) {
    for (const field of schema.required) {
      if (row.values[field] === '') addFinding(findings, file, row, 'REQUIRED_VALUE', 'ERROR', field, 'Campo obrigatorio vazio');
    }
    for (const field of schema.dates ?? []) {
      const value = row.values[field];
      if (value !== '' && !isDate(value)) addFinding(findings, file, row, 'INVALID_DATE', 'ERROR', field, `Data invalida: ${value}`);
    }
    for (const [field, allowed] of Object.entries(schema.domains ?? {})) {
      const value = row.values[field];
      if (value !== '' && !allowed.includes(value)) addFinding(findings, file, row, 'INVALID_DOMAIN', 'ERROR', field, `Valor fora do dominio: ${value}`);
    }
    for (const [field, value] of Object.entries(row.values)) {
      if (['peso_kg', 'volume_m3', 'paletes', 'peso_embarcado_kg', 'volume_embarcado_m3', 'paletes_embarcados', 'valor_brl', 'cap_kg', 'cap_m3', 'cap_paletes', 'cap_kg_dia', 'cap_m3_dia', 'horas_disponiveis'].includes(field) && value !== '' && !isNumeric(value)) {
        addFinding(findings, file, row, 'INVALID_NUMBER', 'ERROR', field, `Numero invalido: ${value}`);
      }
      if (['peso_kg', 'volume_m3', 'paletes', 'peso_embarcado_kg', 'volume_embarcado_m3', 'paletes_embarcados', 'cap_kg', 'cap_m3', 'cap_paletes', 'cap_kg_dia', 'cap_m3_dia', 'horas_disponiveis'].includes(field) && value !== '' && isNumeric(value) && Number(value) < 0) {
        addFinding(findings, file, row, 'NEGATIVE_PHYSICAL_VALUE', 'ERROR', field, `Valor fisico negativo: ${value}`);
      }
    }
    if (file === 'entregas.csv') {
      const status = row.values.status;
      const hasDate = row.values.data_entrega !== '';
      const hasWeight = row.values.peso_entregue_kg !== '';
      if (status === 'ENTREGUE' && !hasDate) addFinding(findings, file, row, 'DELIVERY_CONTRACT', 'ERROR', 'data_entrega', 'ENTREGUE exige data_entrega');
      if (status === 'ENTREGUE' && !hasWeight) addFinding(findings, file, row, 'DELIVERY_CONTRACT', 'ERROR', 'peso_entregue_kg', 'ENTREGUE exige peso_entregue_kg');
      if (status === 'EM_TRANSITO' && (hasDate || hasWeight)) addFinding(findings, file, row, 'DELIVERY_CONTRACT', 'ERROR', 'status', 'EM_TRANSITO exige data e peso vazios');
    }
    if (file === 'pedidos.csv' && row.values.atualizado_em > cutoff) addFinding(findings, file, row, 'AS_OF_CUTOFF', 'ERROR', 'atualizado_em', 'Versao posterior ao corte inicial');
    if (file === 'entregas.csv' && row.values.data_entrega > '2026-09-27') addFinding(findings, file, row, 'AS_OF_CUTOFF', 'ERROR', 'data_entrega', 'Entrega realizada depois do corte');
  }
}

const references = [
  ['rotas.csv', 'galpao_origem_id', 'galpoes.csv', 'galpao_id'],
  ['frota.csv', 'galpao_base_id', 'galpoes.csv', 'galpao_id'],
  ['capacidade.csv', 'galpao_id', 'galpoes.csv', 'galpao_id'],
  ['disponibilidade.csv', 'veiculo_id', 'frota.csv', 'veiculo_id'],
  ['pedidos.csv', 'rota_id', 'rotas.csv', 'rota_id'],
  ['viagens.csv', 'rota_id', 'rotas.csv', 'rota_id'],
  ['viagem_pedidos.csv', 'viagem_id', 'viagens.csv', 'viagem_id'],
  ['viagem_pedidos.csv', 'pedido_id', 'pedidos.csv', 'pedido_id'],
  ['entregas.csv', 'pedido_id', 'pedidos.csv', 'pedido_id'],
  ['entregas.csv', 'viagem_id', 'viagens.csv', 'viagem_id'],
  ['custos.csv', 'viagem_id', 'viagens.csv', 'viagem_id']
];
for (const [source, sourceField, target, targetField] of references) {
  const targetValues = new Set((tables.get(target) ?? []).map(row => row.values[targetField]));
  for (const row of tables.get(source) ?? []) {
    const value = row.values[sourceField];
    if (value !== '' && !targetValues.has(value)) addFinding(findings, source, row, 'FOREIGN_KEY', 'ERROR', sourceField, `Referencia inexistente em ${target}: ${value}`);
  }
}

for (const finding of findings) {
  const rows = tables.get(finding.file) ?? [];
  const row = rows.find(candidate => String(candidate.lineNumber) === String(finding.line_number));
  if (!row) continue;
  if (!quarantine.has(finding.file)) quarantine.set(finding.file, new Map());
  const fileQuarantine = quarantine.get(finding.file);
  if (!fileQuarantine.has(row.lineNumber)) {
    fileQuarantine.set(row.lineNumber, { ...row.values, _line_number: row.lineNumber, _rule: finding.rule, _field: finding.field, _message: finding.message });
  } else {
    const quarantinedRow = fileQuarantine.get(row.lineNumber);
    quarantinedRow._rule += `|${finding.rule}`;
    quarantinedRow._field += `|${finding.field}`;
    quarantinedRow._message += `|${finding.message}`;
  }
}

const findingColumns = ['file', 'line_number', 'rule', 'severity', 'field', 'message', 'key'];
writeCsv(path.join(reportDir, 'inventory.csv'), inventory, ['file', 'bytes', 'records', 'columns', 'header']);
writeCsv(path.join(reportDir, 'quality_findings.csv'), findings, findingColumns);
for (const [file, rowMap] of quarantine) {
  const rows = [...rowMap.values()];
  const columns = [...Object.keys(rows[0]).filter(column => !column.startsWith('_')), '_line_number', '_rule', '_field', '_message'];
  writeCsv(path.join(quarantineDir, file), rows, columns);
}

const summary = {
  generated_at: new Date().toISOString(),
  source_dir: path.relative(projectRoot, sourceDir),
  cutoff,
  files: inventory.length,
  records: inventory.reduce((total, item) => total + item.records, 0),
  findings: findings.length,
  findings_by_rule: Object.fromEntries(Object.entries(Object.groupBy(findings, finding => finding.rule)).map(([rule, items]) => [rule, items.length])),
  quarantined_files: quarantine.size,
  raw_files_modified: false
};
fs.mkdirSync(reportDir, { recursive: true });
fs.writeFileSync(path.join(reportDir, 'quality_summary.json'), JSON.stringify(summary, null, 2) + '\n', 'utf8');
console.log(JSON.stringify(summary, null, 2));

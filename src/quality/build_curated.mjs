import fs from 'node:fs';
import path from 'node:path';

const projectRoot = path.resolve(import.meta.dirname, '..', '..');
const sourceDir = path.join(projectRoot, 'outputs', 'candidato', 'dados', 'base');
const curatedDir = path.join(projectRoot, 'data', 'curated');
const reportDir = path.join(projectRoot, 'reports', 'quality');
const cutoff = '2026-09-27T23:59:59-03:00';

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
    line_number: index + 2,
    ...Object.fromEntries(headers.map((header, position) => [header, values[position] ?? '']))
  }));
}

function readCsv(file) {
  return parseCsv(fs.readFileSync(path.join(sourceDir, file), 'utf8'));
}

function csvEscape(value) {
  const text = String(value ?? '');
  return /[;"\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function writeCsv(file, rows, columns = rows.length ? Object.keys(rows[0]) : []) {
  const content = [columns.join(';'), ...rows.map(row => columns.map(column => csvEscape(row[column])).join(';'))].join('\n') + '\n';
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content, 'utf8');
}

function sumBy(rows, field) {
  return rows.reduce((total, row) => total + Number(row[field] || 0), 0);
}

function addCount(counts, key, amount = 1) {
  counts[key] = (counts[key] ?? 0) + amount;
}

function isValidDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const calendarDate = new Date(Date.UTC(year, month - 1, day));
  return calendarDate.getUTCFullYear() === year && calendarDate.getUTCMonth() === month - 1 && calendarDate.getUTCDate() === day;
}

const pedidos = readCsv('pedidos.csv');
const rotas = readCsv('rotas.csv');
const aliases = readCsv('aliases_rotas.csv');
const custos = readCsv('custos.csv');
const viagens = readCsv('viagens.csv');
const previsoes = readCsv('previsao_manual.csv');

const routes = new Map(rotas.map(row => [row.rota_id, row]));
const aliasMap = new Map(aliases.map(row => [row.alias.trim().toLowerCase(), row.rota_id]));
function normalizeRoute(value) {
  const trimmed = value.trim();
  return routes.has(trimmed) ? trimmed : aliasMap.get(trimmed.toLowerCase()) ?? null;
}

const exclusionCounts = {};
const duplicateOrderKeys = new Set();
const orderKeyGroups = new Map();
for (const row of pedidos) {
  const key = `${row.pedido_id}|${row.versao}`;
  if (!orderKeyGroups.has(key)) orderKeyGroups.set(key, []);
  orderKeyGroups.get(key).push(row);
}
for (const [key, rows] of orderKeyGroups) if (rows.length > 1) duplicateOrderKeys.add(key);

const selectedByOrder = new Map();
for (const row of pedidos) {
  const key = `${row.pedido_id}|${row.versao}`;
  if (duplicateOrderKeys.has(key)) { addCount(exclusionCounts, 'pedido_chave_duplicada'); continue; }
  if (row.atualizado_em > cutoff) { addCount(exclusionCounts, 'pedido_conhecido_apos_corte'); continue; }
  const current = selectedByOrder.get(row.pedido_id);
  if (!current || row.atualizado_em > current.atualizado_em || (row.atualizado_em === current.atualizado_em && Number(row.versao) > Number(current.versao))) selectedByOrder.set(row.pedido_id, row);
}

const validOrders = [];
const excludedOrders = [];
for (const row of selectedByOrder.values()) {
  const routeId = normalizeRoute(row.rota_id);
  const missing = ['pedido_id', 'versao', 'atualizado_em', 'data_coleta', 'data_prometida', 'peso_kg', 'volume_m3', 'paletes', 'status'].filter(field => row[field] === '');
  const reasons = [];
  if (missing.length) reasons.push(`campo_obrigatorio:${missing.join(',')}`);
  if (!isValidDate(row.data_coleta)) reasons.push('data_coleta_invalida');
  if (!isValidDate(row.data_prometida)) reasons.push('data_prometida_invalida');
  for (const field of ['peso_kg', 'volume_m3', 'paletes']) {
    if (row[field] !== '' && Number(row[field]) < 0) reasons.push(`valor_fisico_negativo:${field}`);
  }
  if (!routeId) reasons.push('rota_inexistente_ou_alias_nao_aprovado');
  if (!['CONFIRMADO', 'CANCELADO'].includes(row.status)) reasons.push('status_fora_do_dominio');
  if (reasons.length) {
    excludedOrders.push({ ...row, motivo_exclusao: reasons.join('|') });
    for (const reason of reasons) addCount(exclusionCounts, reason.split(':')[0]);
    continue;
  }
  validOrders.push({ ...row, rota_id_normalizada: routeId });
}

const ordersColumns = [...Object.keys(validOrders[0]).filter(column => column !== 'line_number'), 'line_number'];
writeCsv(path.join(curatedDir, 'pedidos_elegiveis.csv'), validOrders, ordersColumns);
writeCsv(path.join(reportDir, 'pedidos_excluidos.csv'), excludedOrders);

function demandRows(type) {
  const rows = validOrders.filter(row => row.status === 'CONFIRMADO' && (type === 'historica' ? row.data_coleta <= '2026-09-27' : row.data_coleta > '2026-09-27'));
  const groups = new Map();
  for (const row of rows) {
    const galpaoId = routes.get(row.rota_id_normalizada).galpao_origem_id;
    const key = `${row.data_coleta}|${row.rota_id_normalizada}|${galpaoId}`;
    if (!groups.has(key)) groups.set(key, { data: row.data_coleta, rota_id: row.rota_id_normalizada, galpao_id: galpaoId, kg: 0, m3: 0, paletes: 0, pedidos: 0 });
    const group = groups.get(key);
    group.kg += Number(row.peso_kg);
    group.m3 += Number(row.volume_m3);
    group.paletes += Number(row.paletes);
    group.pedidos += 1;
  }
  return [...groups.values()].map(row => ({ ...row, kg: row.kg.toFixed(1), m3: row.m3.toFixed(2), paletes: row.paletes.toFixed(0) }));
}
writeCsv(path.join(curatedDir, 'demanda_historica_diaria.csv'), demandRows('historica'));
writeCsv(path.join(curatedDir, 'carteira_confirmada_diaria.csv'), demandRows('carteira'));

const validTripIds = new Set(viagens.map(row => row.viagem_id));
const costKeyGroups = new Map();
for (const row of custos) {
  if (!costKeyGroups.has(row.lancamento_id)) costKeyGroups.set(row.lancamento_id, []);
  costKeyGroups.get(row.lancamento_id).push(row);
}
const duplicateCostIds = new Set([...costKeyGroups].filter(([, rows]) => rows.length > 1).map(([key]) => key));
const validCosts = custos.filter(row => !duplicateCostIds.has(row.lancamento_id) && validTripIds.has(row.viagem_id));
addCount(exclusionCounts, 'custo_lancamento_duplicado', custos.filter(row => duplicateCostIds.has(row.lancamento_id)).length);
addCount(exclusionCounts, 'custo_viagem_inexistente', custos.filter(row => !validTripIds.has(row.viagem_id)).length);
const costGroups = new Map();
for (const row of validCosts) {
  const key = `${row.viagem_id}|${row.componente}`;
  if (!costGroups.has(key)) costGroups.set(key, { viagem_id: row.viagem_id, componente: row.componente, valor_brl: 0 });
  costGroups.get(key).valor_brl += Number(row.valor_brl);
}
const componentNames = ['VARIAVEL_PROPRIO', 'FRETE_BASE', 'ADICIONAL_EMERGENCIAL', 'PEDAGIO'];
const costsByTrip = new Map();
for (const row of costGroups.values()) {
  if (!costsByTrip.has(row.viagem_id)) costsByTrip.set(row.viagem_id, { viagem_id: row.viagem_id, custo_variavel_proprio_brl: 0, frete_base_brl: 0, adicional_emergencial_brl: 0, pedagio_brl: 0 });
  const output = costsByTrip.get(row.viagem_id);
  const target = { VARIAVEL_PROPRIO: 'custo_variavel_proprio_brl', FRETE_BASE: 'frete_base_brl', ADICIONAL_EMERGENCIAL: 'adicional_emergencial_brl', PEDAGIO: 'pedagio_brl' }[row.componente];
  if (componentNames.includes(row.componente)) output[target] += row.valor_brl;
}
const costsOutput = [...costsByTrip.values()].map(row => ({ ...row, custo_variavel_operacional_brl: row.custo_variavel_proprio_brl + row.frete_base_brl + row.adicional_emergencial_brl + row.pedagio_brl }));
writeCsv(path.join(curatedDir, 'custos_por_viagem.csv'), costsOutput.map(row => Object.fromEntries(Object.entries(row).map(([key, value]) => [key, typeof value === 'number' ? value.toFixed(2) : value]))));

const eligibleForecasts = previsoes.filter(row => row.editado_em <= cutoff).map(row => ({ ...row, rota_id_normalizada: normalizeRoute(row.rota_digitada) })).filter(row => row.rota_id_normalizada);
const forecastGroups = new Map();
for (const row of eligibleForecasts) {
  const key = `${row.semana_inicio}|${row.rota_id_normalizada}`;
  const current = forecastGroups.get(key);
  if (!current || row.editado_em > current.editado_em || (row.editado_em === current.editado_em && Number(row.versao) > Number(current.versao))) forecastGroups.set(key, row);
}
const forecastOutput = [...forecastGroups.values()].map(row => ({ ...row, demanda_kg: (Number(row.demanda_digitada) * (row.unidade === 't' ? 1000 : 1)).toFixed(1), metodo: 'MANUAL_TOTAL_AS_OF_CUTOFF', data_corte: cutoff }));
writeCsv(path.join(curatedDir, 'previsao_manual_elegivel.csv'), forecastOutput);

const summary = {
  generated_at: new Date().toISOString(),
  cutoff,
  selected_orders: validOrders.length,
  excluded_orders: excludedOrders.length,
  historical_demand_rows: demandRows('historica').length,
  backlog_rows: demandRows('carteira').length,
  valid_cost_rows: validCosts.length,
  cost_trips: costsOutput.length,
  eligible_manual_forecasts: forecastOutput.length,
  exclusions: exclusionCounts,
  raw_files_modified: false,
  curated_outputs: ['pedidos_elegiveis.csv', 'demanda_historica_diaria.csv', 'carteira_confirmada_diaria.csv', 'custos_por_viagem.csv', 'previsao_manual_elegivel.csv']
};
fs.mkdirSync(reportDir, { recursive: true });
fs.writeFileSync(path.join(reportDir, 'curation_summary.json'), JSON.stringify(summary, null, 2) + '\n', 'utf8');
console.log(JSON.stringify(summary, null, 2));

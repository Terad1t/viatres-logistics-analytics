import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.resolve('.');
const payload=JSON.parse(await fs.readFile(path.join(root,'work/workbook_data.json'),'utf8'));
const wb=Workbook.create();
const intro=wb.worksheets.add('Leia primeiro');
intro.showGridLines=false;
intro.getRange('A2:B10').values=[
 ['ViaTres | Planilhas operacionais',null],
 ['Conteudo','Copia de apoio; CSV e a fonte autoritativa.'],
 ['Origem','Dados inteiramente sinteticos para avaliacao.'],
 ['Corte','27/09/2026 23:59:59 America/Sao_Paulo'],
 ['Horizonte','28/09/2026 a 04/10/2026'],
 ['Previsao manual','Estimativa TOTAL; inclui carteira conhecida.'],
 ['Versoes e unidades','Preservadas como fonte: resolver no pipeline.'],
 ['Historico completo','Disponivel na pasta dados/base em CSV.'],
 ['Documentacao','Leia briefing, dicionario, KPIs e criterios.']
];
intro.getRange('A2:B10').format.font={name:'Arial',size:11,color:'#243746'};
intro.getRange('A2').format.font={name:'Arial',size:15,bold:true};
intro.getRange('A3:A10').format.font.bold=true;
intro.getRange('A2:A10').format.columnWidth=38;
intro.getRange('B2:B10').format.columnWidth=66;
intro.getRange('A2:B10').format.rowHeight=25;
const dateCols=new Set(['semana_inicio','vigencia_inicio','vigencia_fim']);
const sheets=[intro];
for(const [name,rows] of Object.entries(payload)){
 const sh=wb.worksheets.add(name);sheets.push(sh);sh.showGridLines=false;
 const heads=Object.keys(rows[0]);
 const matrix=[heads,...rows.map(row=>heads.map(h=>dateCols.has(h)?new Date(row[h]+'T00:00:00Z'):h.endsWith('_em')?new Date(row[h].slice(0,19)+'Z'):row[h]))];
 const range=sh.getRangeByIndexes(0,0,matrix.length,heads.length);range.values=matrix;
 range.format.font={name:'Arial',size:10,color:'#243746'};
 range.format.rowHeight=23;
 sh.getRangeByIndexes(0,0,1,heads.length).format={fill:'#183B56',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:36,wrapText:true};
 for(let i=0;i<heads.length;i++){
  const h=heads[i];const col=sh.getRangeByIndexes(0,i,matrix.length,1);
  col.format.columnWidth=h==='observacao'?82:h.endsWith('_em')?34:Math.max(16,Math.min(40,h.length+4));
  if(dateCols.has(h))sh.getRangeByIndexes(1,i,rows.length,1).setNumberFormat('dd/mm/yyyy');
  else if(h.endsWith('_em'))sh.getRangeByIndexes(1,i,rows.length,1).setNumberFormat('dd/mm/yyyy hh:mm "(-03:00)"');
  else if(typeof rows[0][h]==='number')sh.getRangeByIndexes(1,i,rows.length,1).setNumberFormat(h==='demanda_digitada'?'#,##0.0000':h.endsWith('_pct')?'0.0%':Number.isInteger(rows[0][h])?'#,##0':'#,##0.00');
 }
 sh.freezePanes.freezeRows(1);
 sh.tables.add(sh.getUsedRange().address.split('!').pop(),true,'Fonte_'+name);
}
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'previsao_manual!A25:G30',include:'values,formulas',tableMaxRows:6,tableMaxCols:7,maxChars:1600})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},maxChars:1000})).ndjson);
for(const sh of sheets){
 const view=await wb.render({sheetName:sh.name,range:sh===intro?'A1:B11':`A1:${sh.name==='previsao_manual'?'J':sh.name==='rotas'?'J':sh.name==='frota'?'H':sh.name==='tarifas'?'H':'F'}7`,scale:1,format:'png'});
 await fs.writeFile(path.join(root,'work',`preview_${sh.name.replaceAll(' ','_')}.png`),new Uint8Array(await view.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);
await file.save(path.join(root,'outputs/simulacao_logistica/candidato/planilhas_operacionais.xlsx'));
console.log('XLSX exportado; 6 abas inspecionadas e renderizadas.');

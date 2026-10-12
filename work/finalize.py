import csv,json,zipfile,hashlib,math
from pathlib import Path
from datetime import datetime
import openpyxl
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs'; P=OUT/'simulacao_logistica'; C=P/'candidato'; E=P/'avaliador_RESTRITO'
def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter=';'))
def savecsv(path,rs):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rs[0]),delimiter=';');w.writeheader();w.writerows(rs)
payload=json.loads((ROOT/'work/workbook_data.json').read_text(encoding='utf-8'))
wb=openpyxl.load_workbook(C/'planilhas_operacionais.xlsx',read_only=True,data_only=False)
assert len(wb.sheetnames)==6
count=0
for name,rs in payload.items():
    ws=wb[name]; actual=list(ws.values); headers=list(rs[0]);assert list(actual[0])==headers
    assert len(actual)==len(rs)+1
    for values,expected in zip(actual[1:],rs):
        for h,a in zip(headers,values):
            b=expected[h]
            if isinstance(a,datetime): assert a.strftime('%Y-%m-%dT%H:%M:%S')==b[:19] if h.endswith('_em') else a.date().isoformat()==b
            elif isinstance(b,(float,int)): assert math.isclose(a,b,abs_tol=1e-7)
            else:assert a==b,(name,h,a,b)
            count+=1
wb.close()
# Remove only known automatic authoring sidecar, not a user deliverable.
sidecar=C/'planilhas_operacionais.xlsx.inspect.ndjson'
if sidecar.exists():sidecar.unlink()
fixtures=[
 dict(caso='C01_JOIN',entrada='Viagem A: 1000 frete + 100 pedagio; 2 pedidos 600kg e 400kg',esperado='Total 1100 BRL, 1000 kg, 1.10 BRL/kg; nao 2200 BRL',tolerancia='0.01 BRL'),
 dict(caso='C02_OTIF',entrada='4 pedidos expedidos: A integral no prazo; B parcial no prazo; C integral atrasado; D vencido em transito',esperado='Pontualidade 2/4=50%; OTIF 1/4=25%',tolerancia='0.1 pp'),
 dict(caso='C03_CAPACIDADE',entrada='Carga 7000kg, 50m3, 10 paletes; caminhao 8000kg,45m3,14 paletes',esperado='Inviavel em 1 viagem; minimo teorico 2 pelo volume',tolerancia='exato'),
 dict(caso='C04_PREVISAO',entrada='Real [100,200]; previsto [120,180]',esperado='WAPE 40/300=13.3333%; vies 0%; MAE 20',tolerancia='0.1 pp'),
 dict(caso='C05_CARTEIRA',entrada='Previsao TOTAL 1000kg, carteira incluida 400kg',esperado='Total 1000kg, componente ainda nao confirmado 600kg; nao 1400kg',tolerancia='0.1 kg'),
 dict(caso='C06_CUSTO',entrada='Emergencial 2000 base+760 adicional+100 pedagio; proprio 900 variavel+100 pedagio; fixo existente 420',esperado='Economia incremental potencial 1860 BRL; fixo nao evitavel nao se soma a economia',tolerancia='0.01 BRL'),
 dict(caso='C07_OBRA',entrada='G01 nominal 42000kg/225m3; efetiva em 29/09 12600kg/67.5m3; demanda 15000kg/60m3',esperado='Deficit 2400kg, sem deficit volume; nao descontar obra duas vezes',tolerancia='0.1 kg'),
 dict(caso='C08_REPLAY',entrada='A v1 500kg confirmado; lote A v2 cancelado + B v1 200kg confirmado; reaplicar',esperado='2 entidades, demanda liquida 200kg; reaplicacao nao altera',tolerancia='exato'),
 dict(caso='C09_ZERO',entrada='Real [0,0]; previsto [10,0]',esperado='WAPE indisponivel; MAE 5; nao WAPE 0%',tolerancia='exato')]
savecsv(E/'microcenarios_numericos.csv',fixtures)
with (E/'LEIA_PRIMEIRO_AVALIADOR.md').open('a',encoding='utf-8') as f:f.write('\n## Casos numericos isolados\nUse microcenarios_numericos.csv para verificar formulas e limites com entradas pequenas, independentes dos totais do gerador. Sao gabaritos de teste, nao implementacoes.\n')
checks=json.loads((ROOT/'work/checks.json').read_text(encoding='utf-8'))
checks['xlsx_verificado']={'abas':6,'celulas_de_fonte_comparadas':count,'tipos_datas':'datas numericas; timestamps exibidos em -03:00','revisao_visual':'6 abas renderizadas e revisadas; datas/horas corrigidas antes da exportacao final','erros_de_formula':0,'teste_excel_desktop':'Nao executado; validacao por leitura independente do XLSX'}
checks['microcenarios_numericos']=len(fixtures)
# Validate packaged source counts, manifest occurrences and withheld target isolation.
assert len(rows(E/'manifesto_anomalias.csv'))==17
assert len(rows(E/'holdout/alvo_diario.csv'))==84
assert len(rows(C/'documentacao/dicionario_dados.csv'))==107
assert len(rows(C/'dados/base/pedidos.csv'))==44012
assert len(rows(C/'dados/incremental/pedidos_lote_2026-09-28.csv'))==2
checks['testes'].extend(['XLSX relido e comparado celula a celula com fontes copiadas','Holdout tem 84 dias-rota','Contagens de CSVs relidas','ZIPs verificados por CRC e SHA256'])
(P/'verificacao_pacote.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
def manifest(folder):
    rs=[]
    for f in sorted(folder.rglob('*')):
        if f.is_file() and f.name!='MANIFESTO_SHA256.csv':rs.append(dict(arquivo=f.relative_to(folder).as_posix(),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    savecsv(folder/'MANIFESTO_SHA256.csv',rs)
manifest(C);manifest(P)
def pack(folder,target):
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in sorted(folder.rglob('*')):
            if f.is_file():z.write(f,f.relative_to(folder).as_posix())
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for rec in rows(folder/'MANIFESTO_SHA256.csv'):assert hashlib.sha256(z.read(rec['arquivo'])).hexdigest()==rec['sha256']
        if folder==C:assert not any('holdout' in n or 'RESTRITO' in n or 'referencia_limpa' in n for n in z.namelist())
    return dict(arquivo=target.name,bytes=target.stat().st_size)
print(json.dumps({'xlsx_cells_checked':count,'zips':[pack(C,OUT/'candidato.zip'),pack(P,OUT/'pacote_completo_logistica.zip')]},ensure_ascii=False))

import csv, json, math, random, hashlib, zipfile, copy
from pathlib import Path
from datetime import date, datetime, timedelta
from collections import defaultdict, Counter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'
PKG=OUT/'simulacao_logistica'
C=PKG/'candidato'; E=PKG/'avaliador_RESTRITO'
for p in [C/'dados/base', C/'dados/incremental', C/'documentacao', E/'referencia_limpa', E/'holdout']: p.mkdir(parents=True,exist_ok=True)
rng=random.Random(27102026)
START=date(2025,1,1); CUT=date(2026,9,27); END=date(2026,10,4)
ASOF='2026-09-27T23:59:59-03:00'
def days(a,b):
    for n in range((b-a).days+1): yield a+timedelta(days=n)
def stamp(d,h=18): return f'{d.isoformat()}T{h:02}:00:00-03:00'
def writecsv(path,rows,fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or list(rows[0])
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter=';'); w.writeheader(); w.writerows(rows)
def md(path,text): path.write_text(text.strip()+'\n',encoding='utf-8')

data={}
data['galpoes']=[dict(galpao_id=f'G{i+1:02}',uf=uf,cidade=city,capacidade_expedicao_kg_dia=kg,capacidade_expedicao_m3_dia=m3,docas=docas) for i,(uf,city,kg,m3,docas) in enumerate([
    ('SP','Campinas',42000,225,6),('SP','Guarulhos',38000,210,5),('MG','Contagem',32000,180,5),('MG','Uberlandia',28000,165,4),('RJ','Duque de Caxias',32000,185,5),('RJ','Volta Redonda',25000,145,4)])]
dest=[('SP','Ribeirao Preto',230),('MG','Pouso Alegre',200),('RJ','Resende',280),('SP','Sao Jose dos Campos',95),('MG','Juiz de Fora',270),('MG','Divinopolis',125),('SP','Franca',280),('MG','Uberaba',110),('RJ','Campos dos Goytacazes',260),('RJ','Niteroi',55),('SP','Taubate',195),('RJ','Nova Iguacu',110)]
data['rotas']=[dict(rota_id=f'R{i+1:02}',galpao_origem_id=f'G{i//2+1:02}',uf_destino=uf,cidade_destino=city,km_ciclo=km*2,horas_ciclo=round(km*2/55+3,1),sla_dias=1 if km<150 else 2,cap_kg=8000,cap_m3=45,cap_paletes=14) for i,(uf,city,km) in enumerate(dest)]
data['frota']=[dict(veiculo_id=f'V{i+1:03}',galpao_base_id=f'G{i//8+1:02}',tipo='TRUCK',cap_kg=8000,cap_m3=45,cap_paletes=14,custo_fixo_dia_brl=420,custo_variavel_km_brl=2.65) for i in range(48)]
data['tarifas']=[dict(rota_id=r['rota_id'],vigencia_inicio='2025-01-01',vigencia_fim='2026-12-31',frete_regular_ciclo_brl=round(550+r['km_ciclo']*4.1,2),adicional_emergencial_pct=0.38,pedagio_ciclo_brl=round(r['km_ciclo']*.17,2),limite_regular_viagens_dia=2,antecedencia_regular_h=48) for r in data['rotas']]
data['calendario']=[dict(data=d.isoformat(),dia_semana=d.isoweekday(),fator_operacao=1 if d.weekday()<5 else .45 if d.weekday()==5 else 0,observacao='Sem expedicao aos domingos; calendario interno sintetico') for d in days(START,END)]
data['disponibilidade']=[]; avail={}
for d in days(START,END):
    for v in data['frota']:
        vid=v['veiculo_id']; maintenance=rng.random()<.065 or (d>CUT and v['galpao_base_id']=='G03' and int(vid[1:])%3==0)
        status='FECHADO' if d.weekday()==6 else 'MANUTENCAO' if maintenance else 'DISPONIVEL'
        hours=0 if status!='DISPONIVEL' else 16
        avail[(d,vid)]=hours
        data['disponibilidade'].append(dict(data=d.isoformat(),veiculo_id=vid,status=status,horas_disponiveis=hours,natureza='PLANEJADO' if d>CUT else 'REALIZADO',registrado_em=stamp(min(d,CUT),6)))
data['capacidade']=[]
for d in days(START,END):
    for g in data['galpoes']:
        factor=0 if d.weekday()==6 else .6 if d.weekday()==5 else 1
        if g['galpao_id']=='G01' and date(2026,9,28)<=d<=date(2026,9,30): factor*=.30
        data['capacidade'].append(dict(data=d.isoformat(),galpao_id=g['galpao_id'],cap_kg_dia=round(g['capacidade_expedicao_kg_dia']*factor),cap_m3_dia=round(g['capacidade_expedicao_m3_dia']*factor,2),natureza='PLANEJADO' if d>CUT else 'REALIZADO',motivo='OBRA_DOCAS' if g['galpao_id']=='G01' and d>CUT and d.day<=30 and d.month==9 else 'CALENDARIO',registrado_em=stamp(min(d,CUT),6)))
data['eventos_planejados']=[dict(evento_id='EV01',rota_id='R05',inicio='2026-09-28',fim='2026-10-03',impacto_demanda_pct=.35,registrado_em='2026-09-24T10:00:00-03:00',descricao='Campanha comercial confirmada; uplift e hipotese, nao pedido nem realizado')]
orders=[]; deliveries=[]; trips=[]; costs=[]; links=[]; future=[]
oid=tid=did=cid=0
for d in days(START,END):
    if d.weekday()==6: continue
    used=set()
    for ri,r in enumerate(data['rotas']):
        trend=1+ .18*((d-START).days/635)
        seasonal=1+.13*math.sin(2*math.pi*(d.timetuple().tm_yday-210)/365)
        weekday=[1.2,1.03,.97,1.02,1.13,.42,0][d.weekday()]
        campaign=1.35 if d>CUT and r['rota_id']=='R05' else 1
        n=max(2,round((5+ri%4)*trend*seasonal*weekday*campaign*rng.uniform(.8,1.2)))
        active=[]
        for _ in range(n):
            oid+=1; lead=rng.choice([0,1,2,3,5]); created=d-timedelta(days=lead)
            kg=round(rng.uniform(250,1600),1); m3=round(kg/rng.uniform(130,330),2); pallets=max(1,math.ceil(m3/3.2))
            canceled=rng.random()<.035
            row=dict(pedido_id=f'P{oid:07}',versao=1,criado_em=stamp(created,8),atualizado_em=stamp(created,8),rota_id=r['rota_id'],cliente_id=f'C{rng.randint(1,180):03}',data_coleta=d.isoformat(),data_prometida=(d+timedelta(days=r['sla_dias'])).isoformat(),peso_kg=kg,volume_m3=m3,paletes=pallets,status='CANCELADO' if canceled else 'CONFIRMADO')
            if d>CUT:
                future.append(copy.deepcopy(row))
                if created<=CUT: orders.append(row)
            else: orders.append(row)
            if not canceled: active.append(row)
        if d>CUT: continue
        groups=[]; group=[]; load=[0,0,0]
        for o in active:
            q=[o['peso_kg'],o['volume_m3'],o['paletes']]
            if group and any(load[i]+q[i]>[8000,45,14][i] for i in range(3)):
                groups.append(group); group=[];load=[0,0,0]
            group.append(o);load=[load[i]+q[i] for i in range(3)]
        if group: groups.append(group)
        for group in groups:
            tid+=1; tripid=f'T{tid:06}'
            choices=[v for v in data['frota'] if v['galpao_base_id']==r['galpao_origem_id'] and v['veiculo_id'] not in used and avail[(d,v['veiculo_id'])]>=r['horas_ciclo']]
            # Contratacao terceirizada por planejamento manual, mesmo com frota ociosa.
            own=bool(choices) and rng.random()>.25
            v=choices[0] if own else None
            if own: used.add(v['veiculo_id'])
            mode='PROPRIO' if own else ('EMERGENCIAL' if rng.random()<.6 else 'REGULAR')
            trips.append(dict(viagem_id=tripid,rota_id=r['rota_id'],data_saida=d.isoformat(),veiculo_id=v['veiculo_id'] if own else '',modalidade=mode,cap_kg=8000,cap_m3=45,cap_paletes=14,km_ciclo=r['km_ciclo'],horas_ciclo=r['horas_ciclo']))
            tariff=data['tarifas'][ri]
            base=round(r['km_ciclo']*2.65,2) if own else tariff['frete_regular_ciclo_brl']
            components=[('VARIAVEL_PROPRIO' if own else 'FRETE_BASE',base),('PEDAGIO',tariff['pedagio_ciclo_brl'])]
            if mode=='EMERGENCIAL': components.append(('ADICIONAL_EMERGENCIAL',round(base*.38,2)))
            for comp,val in components:
                cid+=1; costs.append(dict(lancamento_id=f'L{cid:07}',viagem_id=tripid,competencia=d.isoformat(),componente=comp,valor_brl=val,registrado_em=stamp(d,20)))
            for o in group:
                links.append(dict(viagem_id=tripid,pedido_id=o['pedido_id'],peso_embarcado_kg=o['peso_kg'],volume_embarcado_m3=o['volume_m3'],paletes_embarcados=o['paletes']))
                promised=date.fromisoformat(o['data_prometida']); late=rng.random()<(.18 if mode=='EMERGENCIAL' else .08)
                delivered=promised+timedelta(days=1 if late else 0)
                did+=1
                done=delivered<=CUT
                partial=done and rng.random()<.025
                deliveries.append(dict(entrega_id=f'D{did:07}',pedido_id=o['pedido_id'],viagem_id=tripid,data_entrega=delivered.isoformat() if done else '',peso_entregue_kg=round(o['peso_kg']*(.85 if partial else 1),1) if done else '',status='PARCIAL' if partial else 'ENTREGUE' if done else 'EM_TRANSITO',registrado_em=stamp(delivered,20) if done else stamp(d,20)))
data.update(pedidos=orders,viagens=trips,viagem_pedidos=links,entregas=deliveries,custos=costs)
# Planilhas manuais preservam inconsistencias humanas de versao e unidade.
manual=[]
for monday in [date(2026,9,14),date(2026,9,21),date(2026,9,28)]:
    for r in data['rotas']:
        known=[o for o in orders if o['rota_id']==r['rota_id'] and monday-timedelta(days=7)<=date.fromisoformat(o['data_coleta'])<monday and o['status']=='CONFIRMADO' and o['atualizado_em']<=stamp(monday-timedelta(days=3),16)]
        value=round(sum(o['peso_kg'] for o in known)*rng.uniform(.86,1.05),1)
        manual.append(dict(planilha_id=f'M{len(manual)+1:03}',semana_inicio=monday.isoformat(),rota_digitada=r['rota_id'],demanda_digitada=value,unidade='kg',versao=1,editado_em=stamp(monday-timedelta(days=3),16),responsavel='Equipe_'+r['galpao_origem_id'],observacao='Estimativa manual da demanda total; inclui carteira conhecida'))
data['previsao_manual']=manual
data['aliases_rotas']=[dict(alias='r 01',rota_id='R01'),dict(alias='R-05',rota_id='R05')]
clean=copy.deepcopy(data)
issues=[]
def issue(table,rownum,field,new,rule,action):
    row=data[table][rownum]; old=row[field]; row[field]=new
    issues.append(dict(ocorrencia_id=f'Q{len(issues)+1:03}',arquivo=table+'.csv',linha_csv=rownum+2,chave=str(next(iter(row.values()))),campo=field,valor_original=old,valor_injetado=new,regra=rule,tratamento_esperado=action))
issue('pedidos',101,'peso_kg',-450,'Peso estritamente positivo','Quarentena da metrica; nao usar abs nem adivinhar o original')
issue('pedidos',205,'volume_m3','','Volume obrigatorio','Sinalizar ausencia; nao substituir por zero')
issue('pedidos',308,'rota_id','R99','FK inexistente','Quarentena; preservar pedido bruto')
issue('pedidos',412,'data_coleta','2025-02-30','Data invalida','Quarentena de data')
issue('pedidos',511,'status',' confirmado ','Dominio normalizavel','Trim e uppercase com rastreio')
issue('entregas',701,'data_entrega','2024-12-01','Entrega anterior a coleta','Quarentena do prazo')
issue('custos',805,'valor_brl',-75,'Sem estorno neste contrato','Quarentena; pedir comprovante')
issue('custos',901,'viagem_id','T999999','FK inexistente','Quarentena de custo')
issue('disponibilidade',1020,'horas_disponiveis',28,'Horas fora de 0 a 24','Quarentena da capacidade')
issue('previsao_manual',24,'rota_digitada','r 01','Alias cadastrado','Resolver por aliases_rotas')
issue('previsao_manual',28,'rota_digitada','R-05','Alias cadastrado','Resolver por aliases_rotas')
row=data['previsao_manual'][25]; val=row['demanda_digitada']
issue('previsao_manual',25,'demanda_digitada',round(val/1000,4),'Unidade explicita t','Converter toneladas em kg')
issue('previsao_manual',25,'unidade','t','Unidade explicita t','Multiplicar por 1000; tolerancia 0.1 kg')
for tab,idx in [('pedidos',55),('custos',67)]:
    data[tab].append(copy.deepcopy(data[tab][idx])); issues.append(dict(ocorrencia_id=f'Q{len(issues)+1:03}',arquivo=tab+'.csv',linha_csv=len(data[tab])+1,chave=str(next(iter(data[tab][idx].values()))),campo='LINHA',valor_original='1 linha',valor_injetado='duplicata exata',regra='PK duplicada exata',tratamento_esperado='Deduplicar sem dobrar totais'))
rev=copy.deepcopy(data['previsao_manual'][24]);rev.update(planilha_id='M037',versao=2,demanda_digitada=rev['demanda_digitada']*1.1,editado_em='2026-09-26T16:00:00-03:00',observacao='Revisao comercial; substitui versao 1, nao somar')
data['previsao_manual'].append(rev)
issues.append(dict(ocorrencia_id='Q016',arquivo='previsao_manual.csv',linha_csv=38,chave='M037',campo='versao',valor_original='v1 permanece',valor_injetado='v2 legitima',regra='Ultima versao conhecida por semana e rota normalizada',tratamento_esperado='Selecionar v2; nao tratar como duplicata exata'))
# Retirar uma disponibilidade futura: desconhecido nao equivale a indisponivel.
idx=next(i for i,x in enumerate(data['disponibilidade']) if x['data']=='2026-09-29' and x['veiculo_id']=='V040')
missing=data['disponibilidade'].pop(idx)
issues.append(dict(ocorrencia_id='Q017',arquivo='disponibilidade.csv',linha_csv='',chave='2026-09-29|V040',campo='LINHA',valor_original=json.dumps(missing),valor_injetado='ausente',regra='Completude data x frota',tratamento_esperado='Capacidade desconhecida; cobertura explicita'))
for name,rows in data.items(): writecsv(C/'dados/base'/f'{name}.csv',rows)
for name,rows in clean.items(): writecsv(E/'referencia_limpa'/f'{name}.csv',rows)
writecsv(E/'manifesto_anomalias.csv',issues)
writecsv(E/'holdout/demanda_realizada_2026-09-28_a_10-04.csv',future)

# Incremental libera depois de congelar a previsao e e reaplicado identico.
cancel=copy.deepcopy(next(o for o in orders if o['data_coleta']=='2026-09-29' and o['status']=='CONFIRMADO'))
cancel.update(versao=2,status='CANCELADO',atualizado_em='2026-09-28T07:00:00-03:00')
late=copy.deepcopy(orders[300]);late.update(pedido_id='P9000001',criado_em='2026-09-26T08:00:00-03:00',atualizado_em='2026-09-28T06:30:00-03:00',data_coleta='2026-09-26',data_prometida='2026-09-28',status='CONFIRMADO')
writecsv(C/'dados/incremental/pedidos_lote_2026-09-28.csv',[cancel,late])
md(C/'dados/incremental/LEIA_ANTES.md','''# Lote posterior ao corte
Nao carregar na previsao congelada em 27/09/2026. A simulacao avanca para 28/09 as 08h apenas na fase incremental.
O arquivo contem uma nova versao de pedido e um pedido recebido com atraso de ingestao. Reaplique o mesmo arquivo duas vezes. Nao invente entrega ou viagem para o pedido tardio. O holdout reservado representa a fotografia original e nao deve ser comparado a uma previsao refeita depois deste lote.
''')

# Contratos semanticos de todos os campos.
desc={
'galpao_id':'Identificador do galpao; PK no cadastro, FK galpoes nas tabelas diarias', 'uf':'Estado: SP, MG ou RJ','cidade':'Municipio do galpao; rotulos sem acentos no dado',
'capacidade_expedicao_kg_dia':'Capacidade nominal de expedicao por dia, kg; nao e estoque','capacidade_expedicao_m3_dia':'Capacidade nominal de expedicao por dia, m3','docas':'Quantidade de docas; informativa, ja refletida na capacidade',
'rota_id':'Identificador da rota; PK rotas e FK nas demais tabelas','galpao_origem_id':'FK galpoes.galpao_id; origem e retorno do ciclo','uf_destino':'UF do destino','cidade_destino':'Municipio atendido; rota agregada de distribuicao','km_ciclo':'Quilometros totais ida e volta; nao multiplicar por dois','horas_ciclo':'Horas do ciclo incluindo carga e descarga; simplificacao operacional','sla_dias':'Dias corridos entre coleta e promessa',
'cap_kg':'Limite fisico de peso do veiculo/ciclo, kg','cap_m3':'Limite fisico de volume do veiculo/ciclo, m3','cap_paletes':'Limite fisico de posicoes palete por ciclo',
'veiculo_id':'PK frota ou FK frota; vazio em viagem terceirizada','galpao_base_id':'FK galpoes; veiculo retorna a esta base','tipo':'Classe TRUCK nesta simulacao','custo_fixo_dia_brl':'Custo fixo por veiculo por dia corrido, inclusive manutencao e domingo','custo_variavel_km_brl':'Custo por km do proprio, exclui fixos e pedagio',
'vigencia_inicio':'Primeiro dia valido da tarifa, inclusivo','vigencia_fim':'Ultimo dia valido da tarifa, inclusivo','frete_regular_ciclo_brl':'Preco-base contratado por ciclo completo; exclui pedagio','adicional_emergencial_pct':'Fracao adicional sobre frete-base; 0.38 significa 38%','pedagio_ciclo_brl':'Pedagio por ciclo, proprio ou terceiro','limite_regular_viagens_dia':'Limite contratado de viagens regulares por rota/dia para planejamento futuro','antecedencia_regular_h':'Antecedencia minima contratual de reserva em horas',
'data':'Dia operacional local; parte de chave composta nas tabelas diarias','dia_semana':'ISO: segunda=1, domingo=7','fator_operacao':'Fator sintetico de demanda no calendario; nao multiplicar capacidade por este fator','observacao':'Texto contextual; nao compoe chave',
'status':'Dominio especifico da tabela; consultar contrato','horas_disponiveis':'Horas uteis do veiculo/data; 0 a 24; ja inclui manutencao','natureza':'REALIZADO para passado; PLANEJADO para futuro, nunca equivalentes','registrado_em':'Instante em que a fonte disponibilizou o registro, ISO com offset -03:00',
'cap_kg_dia':'Limite efetivo diario kg; substitui nominal, nao se soma a ele','cap_m3_dia':'Limite efetivo diario m3; substitui nominal','motivo':'CALENDARIO ou OBRA_DOCAS; obra ja aplicada ao limite',
'evento_id':'PK do evento planejado','inicio':'Primeiro dia do evento','fim':'Ultimo dia do evento','impacto_demanda_pct':'Hipotese de variacao relativa de demanda; nao e volume adicional confirmado','descricao':'Contexto de evento e grau de certeza',
'pedido_id':'Identificador comercial; chave de entidade, usar com versao na ingestao','versao':'Inteiro crescente; selecionar ultima versao disponivel no corte','criado_em':'Instante original de criacao na fonte','atualizado_em':'Instante de disponibilidade desta versao; filtro as-of','cliente_id':'Identificador sintetico anonimizado, sem cadastro externo','data_coleta':'Dia de demanda/expedicao solicitada; eixo da previsao','data_prometida':'Prazo final de entrega em dias corridos, inclusivo','peso_kg':'Peso solicitado em kg, positivo','volume_m3':'Volume solicitado em m3, positivo','paletes':'Quantidade inteira positiva de paletes solicitados',
'viagem_id':'PK viagens; FK entregas, custos e viagem_pedidos','data_saida':'Dia de saida; base para custo operacional e ocupacao','modalidade':'PROPRIO, REGULAR ou EMERGENCIAL','peso_embarcado_kg':'Kg alocados ao pedido/viagem; nao e peso entregue','volume_embarcado_m3':'M3 alocados ao pedido/viagem','paletes_embarcados':'Paletes alocados ao pedido/viagem',
'entrega_id':'PK do registro de entrega; uma linha por pedido neste recorte','data_entrega':'Dia efetivo da entrega; vazio somente em transito','peso_entregue_kg':'Kg efetivamente recebidos; vazio em transito, nao equivale a zero','lancamento_id':'PK de lancamento contabil de custo; duplicata exata e defeito','competencia':'Dia a que se atribui o custo','componente':'VARIAVEL_PROPRIO, FRETE_BASE, PEDAGIO ou ADICIONAL_EMERGENCIAL','valor_brl':'Valor em BRL com 2 casas; neste pacote nao ha estornos validos',
'planilha_id':'PK da linha manual; nao identifica versao comercial por si so','semana_inicio':'Segunda-feira da semana de demanda prevista','rota_digitada':'Rota livre; resolver alias antes de selecionar versao','demanda_digitada':'Estimativa TOTAL semanal, nao demanda residual; unidade na coluna unidade','unidade':'kg ou t; converter t x 1000','editado_em':'Instante conhecido da revisao manual','responsavel':'Equipe sintetica que alterou a estimativa','alias':'Texto alternativo autorizado; PK aliases_rotas'}
grains={
'galpoes':('galpao_id','Um galpao'),'rotas':('rota_id','Uma rota de distribuicao com retorno a base'),'frota':('veiculo_id','Um veiculo proprio'),
'tarifas':('rota_id + vigencia_inicio','Uma tarifa por rota e intervalo'),'calendario':('data','Um dia do calendario interno'),
'disponibilidade':('data + veiculo_id','Um veiculo por dia'),'capacidade':('data + galpao_id','Um galpao por dia'),
'eventos_planejados':('evento_id','Um evento comercial conhecido'),'pedidos':('pedido_id + versao','Uma versao de pedido; nao item SKU'),
'viagens':('viagem_id','Um ciclo de distribuicao fechado, ida e volta'),'viagem_pedidos':('viagem_id + pedido_id','Alocacao de um pedido numa viagem'),
'entregas':('entrega_id','Uma entrega final/parcial ou em transito por pedido'),'custos':('lancamento_id','Um componente de custo por viagem'),
'previsao_manual':('planilha_id','Uma revisao de estimativa por rota/semana'),'aliases_rotas':('alias','Um alias aprovado')}
nullable={('viagens','veiculo_id'),('entregas','data_entrega'),('entregas','peso_entregue_kg')}
dictrows=[]
for tab,rows in data.items():
    for col,val in rows[0].items():
        typ='decimal' if isinstance(val,float) else 'inteiro' if isinstance(val,int) else 'timestamp ISO8601' if col.endswith('_em') else 'data ISO8601' if col in ['data','inicio','fim','vigencia_inicio','vigencia_fim','competencia','semana_inicio','data_coleta','data_prometida','data_saida','data_entrega'] else 'texto'
        dictrows.append(dict(arquivo=tab+'.csv',campo=col,tipo_esperado=typ,nulo_permitido='SIM_CONDICIONAL' if (tab,col) in nullable else 'NAO',chave_da_tabela=grains[tab][0],descricao=desc[col]))
writecsv(C/'documentacao/dicionario_dados.csv',dictrows)
md(C/'documentacao/03_DICIONARIO_E_CONTRATOS.md', '''# Dicionario e contratos de dados

O arquivo dicionario_dados.csv documenta cada campo. Tipos sao o contrato esperado: o bruto contem violacoes intencionais. Todos os dados sao inventados; nao provem de uma empresa ou fonte real.

## Formato e ingestao
CSV UTF-8 com BOM, separador ponto e virgula, decimal ponto, datas YYYY-MM-DD e timestamps ISO8601 com offset -03:00. Vazio representa desconhecido/nao aplicavel conforme contrato, nunca zero implicito. IDs sao texto e preservam zeros. BRL nominal, sem correcao monetaria ou analise tributaria. Nao ha dados pessoais reais.

## Graos e chaves
'''+ '\n'.join(f'- **{t}.csv**: {g[1]}. Chave: `{g[0]}`. Linhas brutas: {len(data[t]):,}.' for t,g in grains.items())+'''

## Relacionamentos e precedencia
Pedidos → rotas → galpoes. Viagens → rotas; viagem_pedidos liga pedidos e viagens. Neste recorte, cada pedido confirmado historico e embarcado uma vez; cancelados nao embarcam. Entregas se ligam a pedido E viagem, que devem concordar com a ponte. Custos sao N componentes por viagem: agregar antes de juntar a pedidos para evitar multiplicacao. Rateio opcional por peso embarcado, com diferencas de centavos reconciliadas por viagem. Nao confundir entrega parcial com nova demanda.

Frota → galpoes; disponibilidade por veiculo/dia deve cobrir toda a frota ativa (48 veiculos, sem admissoes/baixas). Ausencia de linha nao prova disponibilidade zero. O limite efetivo de capacidade diaria tem precedencia sobre o nominal; obra ja descontada. Limites de veiculo devem valer simultaneamente em kg, m3 e paletes. Nunca somar estas unidades.

Pedidos: CONFIRMADO ou CANCELADO. Disponibilidade: DISPONIVEL, MANUTENCAO ou FECHADO. Entregas: ENTREGUE, PARCIAL ou EM_TRANSITO. No historico, pedidos expedidos continuam CONFIRMADO; o estado de entrega pertence ao TMS. ENTREGUE exige peso integral; PARCIAL exige peso menor e positivo; EM_TRANSITO exige data e peso vazios. A entrega parcial e encerrada para este teste, sem nova tentativa. SLA por dia local inclusivo, sem calendario de feriados reais.

Nao existem feriados nacionais/estaduais no calendario sintetico: e um contrato de operacao, nao uma fonte legal. Domingo sem coleta/expedicao, embora uma entrega em transito possa terminar nesse dia. Um veiculo faz no maximo um ciclo por dia e retorna a base; nao ha realocacao entre galpoes. Horas do ciclo devem caber nas horas disponiveis. Nao modelamos jornada legal de motoristas, estoque em transito, roteirizacao de paradas ou cadeia fria. Nao extrapolar a solucao para operacao real sem revisar essas limitacoes.

## Tempo, fotografias e fontes
Corte de conhecimento: 2026-09-27 23:59:59 America/Sao_Paulo. Pedidos com coleta ate o corte sao historico; os de coleta posterior sao CARTEIRA CONFIRMADA conhecida, nao demanda realizada. O CSV de pedidos mistura esses dois usos propositalmente e exige filtros explicitos. Disponibilidade e capacidade futuras sao PLANOS conhecidos no corte. Previsao manual e sempre estimativa; nao deve entrar no alvo historico.

Base de pedidos e uma fotografia contendo v1; o incremental posterior contem atualizacoes e uma chegada tardia. Sua versao so vale a partir de atualizado_em. Lote entregue ao candidato e elegivel somente na fase posterior. Não ha CDC, exclusao fisica ou trilha completa de alteracoes antigas. Backtests com fotografias antigas de status sao aproximacoes: declarar essa limitacao. Custos historicos foram conhecidos no proprio dia no recorte, com uma violacao artificial de qualidade. Nenhuma entrega apos o corte aparece como realizada na base.

Previsao manual: resolver alias autorizado, converter unidade e escolher maior editado_em elegivel; desempate por versao; conflito residual exige excecao. A chave de negocio e semana + rota normalizada. Nao somar v1 e v2. Estimativa manual e DEMANDA TOTAL, ja incluindo carteira; nao adicionar carteira novamente. Em uma previsao estatistica total, carteira e piso conhecido ou componente explicitamente decomposto, nao parcela automaticamente somada.

## Custos e capacidade
Custos contem variavel proprio, frete-base terceiro, adicional emergencial e pedagio. Fixos da frota estao apenas no cadastro: custo fixo por dia corrido x veiculos. Valor-base regular nao inclui adicional nem pedagio. Tarifas futuras sao hipoteses contratuais do case, nao precos reais de mercado. Limite de dois terceiros regulares por rota/dia e restricao de planejamento futuro; realizado historico pode ter excedido contratos e deve ser descrito, nao reescrito. Emergencial sem teto contratual no exercicio, sujeito a disponibilidade real nao fornecida; nunca prometer que sera contratado.

Galpao limita expedicao, nao armazenagem. Se o plano viola kg OU m3, ha gargalo. Frota sobrando nao resolve automaticamente obra em doca. Cancelados nao entram em demanda liquida. Eventos planejados sao hipoteses: o uplift nao e pedido e nao deve ser aplicado outra vez a uma previsao que ja o incorpora.
''')

md(C/'documentacao/01_BRIEFING_CEO.md', '''# ViaTres Logistica — briefing do CEO

Empresa totalmente ficticia de porte medio. Atendemos 180 clientes identificados apenas por codigo, com seis galpoes em SP, MG e RJ, 48 caminhoes proprios e transportadoras parceiras em 12 rotas. Crescemos sem organizar nossos dados. Vendemos servico de distribuicao de cargas secas B2B; estes arquivos sao um recorte simplificado dessa operacao.

“Toda segunda-feira preciso saber onde vai faltar espaco para carga, quais galpoes e caminhoes estarao sobrecarregados e onde vale a pena reservar frete antes de virar emergencia. Hoje cada equipe manda uma planilha diferente. Algumas previsoes ja incluem pedidos vendidos, outras estao desatualizadas. Pagamos frete urgente enquanto ha caminhao parado em outra base.

Quero uma tela que mostre o risco para a proxima semana, quanto custa cada alternativa e o que minha equipe precisa confirmar. Nao preciso que voce acerte tudo; preciso entender o que sabemos, o que estamos estimando e quando o dado esta velho. Nao quero trocar um Excel por outro grafico que nao muda minha decisao.

Temos uma obra em Campinas e uma campanha comercial saindo de Contagem. Se houver risco, quero saber antes. E quero que voce me explique como vamos medir se economizamos de verdade, sem chamar uma estimativa de dinheiro no caixa.”

## O que o CEO quer decidir
- Quais rotas/dias e galpoes exigem acao na semana de 28/09 a 04/10/2026?
- Quanto da necessidade ja esta confirmado e quanto depende de previsao?
- Reservar frete regular, usar frota disponivel, negociar janela ou esperar? Quais restricoes impedem cada opcao?
- Qual faixa de custo incremental e economia potencial acompanha a sugestao? Quem precisa aprovar?

## Metas de negocio do piloto (hipoteses, nao promessas)
Reduzir em 15% o gasto com adicional emergencial por kg expedido versus referencia comparavel; reduzir em 50% o tempo semanal de consolidacao, cuja referencia declarada e 20 horas da equipe; nao piorar OTIF em mais de 2 pontos percentuais. Validar metas e referencia com operacao/financas antes de aceitar o piloto.

Proposta de prazo a discutir: diagnostico em 1 semana, prototipo em 2–3 semanas e piloto medido por 4–8 semanas apos acesso e validacao das fontes. Sao hipoteses de planejamento, nao SLA ou garantia de economia. O teste local nao prova economia em producao. Primeira entrega deve incluir limite de cobertura e horario de atualizacao. “Tempo real” depende de integracao, disponibilidade das fontes e monitoramento que estes arquivos nao fornecem.
''')

md(C/'documentacao/02_DESAFIO_E_EXECUCAO.md', '''# Desafio e guia de execucao

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
''')

md(C/'documentacao/04_KPIS_E_LIMITES.md', '''# KPIs e limites de interpretacao

Todos os indicadores devem informar populacao, periodo, unidade, cobertura e corte. Quantidades historicas usam data_coleta; custos operacionais usam data_saida/competencia. Nao somar percentuais de rotas: recalcular pelos numeradores e denominadores.

| KPI | Definicao contratual | Limites |
|---|---|---|
| Demanda liquida | Soma de kg, m3 ou paletes de pedidos CONFIRMADO, ultima versao elegivel, por coleta/rota | Cancelado fora. Nao usar entregue como proxy de solicitado. Carteira futura separada. |
| Custo variavel operacional | Soma dos componentes de custos validos no periodo | Inclui pedagio, adicional e frete-base/variavel proprio; nao inclui fixos. |
| Custo total do recorte | Variavel + 420 BRL x 48 veiculos x dias corridos do periodo | Fixos persistem com ociosidade. Nao atribuir economia de fixo sem eliminacao real. |
| Custo por kg expedido | Variavel / peso embarcado das mesmas viagens elegiveis | Agregar custos antes da ponte; cobertura conjunta. Denominador zero = indisponivel. |
| Participacao emergencial | Viagens EMERGENCIAL / viagens totais | Contagem de viagens unicas, nao pedidos. |
| Adicional emergencial por kg | Soma ADICIONAL_EMERGENCIAL / kg expedido do mesmo escopo | Referencia para meta do piloto, nao comparar mix sem ajuste. |
| Ocupacao por peso / volume / paletes | Soma carga embarcada / soma capacidade das viagens, para cada unidade separada | Nao media simples de percentuais. Nao inclui frota que nao saiu. |
| Utilizacao da frota | Veiculos-dia proprios usados / veiculos-dia DISPONIVEL com horas > 0 | Uma viagem por dia no case; ausencias de disponibilidade afetam cobertura. |
| Ociosidade disponivel | Veiculos-dia disponiveis sem viagem / veiculos-dia disponiveis | Nao inclui manutencao; nao e custo evitavel automaticamente. |
| Entrega no prazo | Pedidos com data_entrega <= prometida / pedidos expedidos com prometida <= corte | Pendente vencido conta como falha; futura promessa excluida. Campo invalido deve gerar cobertura, nao sucesso. |
| OTIF | Pedidos da mesma coorte entregues no prazo E integralmente / pedidos expedidos com prometida <= corte | Integral: peso entregue >= solicitado com tolerancia 0.1 kg. Parcial falha, pendente vencido falha. |
| Backlog vencido | Pedidos expedidos com promessa < dia do corte e sem entrega encerrada | PARCIAL e encerrada neste case; nao reconduzir como backlog. |
| WAPE | Soma abs(previsao-real) / soma real | Por horizonte/rota e total, kg e m3 separados; denominador zero = indisponivel. |
| Vies | Soma(previsao-real) / soma real | Positivo = excesso. Informar tambem MAE em unidade fisica. |
| Cobertura de intervalo | Fracao de observacoes dentro do intervalo declarado | Nao nomear “95%” sem metodo/calibracao; avaliar separadamente largura e cobertura. |
| Sobrecarga do galpao | max(0, demanda prevista - cap efetiva) por unidade/dia | Peso e volume ambos limitam; nao compensar excesso diario com folga outro dia sem plano explicito. |
| Necessidade teorica de ciclos | max(ceil(kg/8000), ceil(m3/45), ceil(paletes/14)) | Limite inferior; cargas indivisiveis e roteamento podem exigir mais. Nao prova plano factivel. |
| Frescor | Instante de avaliacao - ultimo instante de fonte recebido | Hora do processamento nao prova atualizacao da origem. Registrar ambos se existentes. |
| Qualidade/cobertura | Registros e valor de negocio elegiveis vs esperados, por metrica | Registro rejeitado em volume pode continuar apto em peso se politica explicita. |

## Economia sem dupla contagem
Economia potencial = custo evitavel de referencia - custo incremental da alternativa - custo de implantacao/operacao alocado, com horizonte e hipoteses declarados. Trocar emergencial por proprio compara frete terceiro evitavel com variavel proprio + pedagio + demais incrementos; fixo existente nao desaparece. Trocar emergencial por regular so evita adicional se houver antecedencia e disponibilidade. Nao somar duas alternativas mutuamente exclusivas. Custo de oportunidade, remanejamento, multa e horas extras nao estao nos dados: cenarios precisam declarar essas lacunas.

Economia realizada exige custo observado contra contrafactual acordado, mesma demanda/mix, periodo piloto, custos de execucao e aceite financeiro. O holdout mede demanda, nao causalidade de economia. Compare semanas equivalentes e explique sazonalidade, mudancas de mix e servico. Nao prometer acuracia perfeita ou SLA de tempo real com arquivos em lote.

## Limites e alertas do case
Alerta de saturacao a partir de 90% do limite efetivo, critico acima de 100%; estes sao limiares acordados para simulacao, nao padroes universais. Dado diario com mais de 24 horas desde disponibilidade conhecida deve aparecer como atrasado, com ressalva para calendario de fontes. Planejamento de disponibilidade futura pode ter idade maior por ser um plano; mostrar emissao e vigencia separadamente, sem chama-lo de telemetria.

Estimativas de desempenho nao sao criterio absoluto de contratacao: exigimos baseline e avaliacao honesta. Um modelo mais complexo so se justifica se melhora as janelas temporais de modo consistente. No holdout final, nao se exige erro abaixo de uma porcentagem arbitraria. Demanda observada e parcialmente determinada pelo gerador sintetico e nao representa a variabilidade de toda logistica brasileira.
''')

md(C/'documentacao/05_VALIDACAO_E_ACEITE.md', '''# Cenarios de validacao e criterios de aceite

| Caso | Procedimento | Evidencia esperada |
|---|---|---|
| V01 Reexecucao | Carregar base duas vezes | Mesmas entidades, totais e resultados; duplicatas brutas rastreadas. |
| V02 Cardinalidade | Juntar custos, viagens e pedidos | Total de custos nao cresce com o numero de pedidos ou componentes. |
| V03 Qualidade | Procurar datas, dominios, FKs, negativos, nulos e duplicatas | Identificacao com arquivo/linha/chave, regra e tratamento; sem correcao inventada. |
| V04 Versoes manuais | Normalizar rota/unidade e selecionar revisao | Uma estimativa por rota/semana; t convertida; v2 substitui v1. |
| V05 Corte | Congelar em 27/09 23:59:59 | Carteira futura separada do realizado; lote posterior excluido; entregas futuras desconhecidas. |
| V06 Atualizacao | Aplicar incremental duas vezes em 28/09 08h | Uma entidade nova, uma entidade atualizada, nenhum aumento na segunda aplicacao; snapshots preservados. |
| V07 Disponibilidade | Cruzar frota x dias futuros | Lacuna nao vira disponibilidade nem zero silencioso; cobertura e intervalo de capacidade. |
| V08 Restricoes | Obra de G01, campanha de R05, manutencao de G03 | Alertas de capacidade por dia/unidade e limite de frota; nao usar caminhao de outra base sem autorizacao. |
| V09 Sem demanda | Incluir domingo e divisores nulos | Demanda contratual zero; WAPE/custo unitario indisponivel se denominador zero, sem erro mascarado. |
| V10 Servico | Parcial, transito, atrasada e prazo futuro | OTIF e pontualidade seguem coorte de promessa; pendente vencido nao desaparece. |
| V11 Stress | +20% demanda e perda de um veiculo/base em 29/09 | Deficits e custos recalculados; restricoes continuam respeitadas. |
| V12 Previsao | Quatro janelas temporais e holdout congelado | Baseline, WAPE, vies, MAE, dados elegiveis e explicacao da incerteza; sem vazamento. |
| V13 Economia | Comparar alternativas mutuamente exclusivas | Fixos nao evitaveis preservados, adicional sem dupla contagem, hipoteses e faixas. |
| V14 Auditabilidade | Escolher um alerta e rastrear dados | Fonte, chave, corte, regra, calculo, acao e responsavel sugerido recuperaveis. |

## Aceite minimo obrigatorio
Execucao reproduzivel; bruto preservado; chaves e graos corretos; duplicatas sem efeito nos totais; invalidos visiveis com tratamento; corte temporal respeitado; lote idempotente; restricoes de capacidade simultaneas; pelo menos uma previsao baseline avaliada; visao que liga gargalo a acao/custo; limites explicitos. Totais devem reconciliar a populacao que o candidato declarou elegivel, nao uma base “ideal” desconhecida.

Tolerancias: contagens/IDs/datas exatos; monetario por lancamento 0.01 BRL, total 0.05 BRL por arredondamento demonstrado; kg 0.1, m3 0.01 por registro; taxas 0.1 ponto percentual por arredondamento. Divergencias de politica de quarentena exigem ponte quantitativa. Valor impossivel nao precisa ser recuperado. Avaliar previsao por evidencia, nao por reproduzir o gerador.

## Rubrica (100 pontos)
- Pipeline, reprocessamento, incremental e rastreabilidade: 25.
- Qualidade, contrato, reconciliacao e juncoes: 20.
- Analytics de custo, servico e capacidade: 20.
- Previsao, baseline, backtest, incerteza e corte: 20.
- Clareza de decisao, execucao e limites: 15.

Referencia de aprovacao: >=75 e todos os criterios minimos. Pontuar cada grupo como ausente (0%), parcial (50%), completo com evidencia (100%), admitindo fracao justificada. Vazamento temporal material, custo multiplicado por join, capacidade fisicamente impossivel apresentada como factivel ou economia garantida sem evidencia impedem aceite ate correcao. Uma tecnologia especifica, dashboard bonito ou modelo complexo nao garantem pontos.
''')

# Expected controls from pre-corruption canonical records; explicitly not a cleaning solution.
controls=[]
def ctl(name,value,unit,scope): controls.append(dict(controle=name,valor=value,unidade=unit,escopo=scope))
hist=[o for o in clean['pedidos'] if o['data_coleta']<=CUT.isoformat() and o['status']=='CONFIRMADO']
book=[o for o in clean['pedidos'] if o['data_coleta']>CUT.isoformat() and o['status']=='CONFIRMADO']
for name,rows in clean.items(): ctl('linhas_antes_injecao_'+name,len(rows),'linhas','Referencia limpa; nao contagem bruta esperada')
ctl('demanda_historica_kg',round(sum(o['peso_kg'] for o in hist),1),'kg','Confirmados com coleta <= 27/09 na referencia limpa')
ctl('demanda_historica_m3',round(sum(o['volume_m3'] for o in hist),2),'m3','Mesmo escopo')
ctl('carteira_futura_kg',round(sum(o['peso_kg'] for o in book),1),'kg','Coleta > corte, conhecido no corte; nao somar ao total previsto')
ctl('custo_variavel_brl',round(sum(x['valor_brl'] for x in clean['custos']),2),'BRL','Todas viagens historicas da referencia limpa')
ctl('custo_fixo_brl',420*48*((CUT-START).days+1),'BRL','Todos veiculos, todos dias corridos 01/01/2025 a 27/09/2026')
od={o['pedido_id']:o for o in hist}; eligible=[x for x in clean['entregas'] if od[x['pedido_id']]['data_prometida']<=CUT.isoformat()]
on=[x for x in eligible if x['data_entrega'] and x['data_entrega']<=od[x['pedido_id']]['data_prometida']]
otif=[x for x in on if x['peso_entregue_kg']>=od[x['pedido_id']]['peso_kg']-.1]
ctl('coorte_servico',len(eligible),'pedidos','Promessa <= corte; expedidos')
ctl('no_prazo',len(on),'pedidos','Numerador de pontualidade na referencia limpa')
ctl('otif',len(otif),'pedidos','Numerador de OTIF na referencia limpa')
ctl('incremental_delta_entidades',1,'pedidos','Primeira aplicacao')
ctl('incremental_delta_entidades_replay',0,'pedidos','Segunda aplicacao do mesmo lote')
ctl('incremental_delta_demanda_confirmada_kg',round(late['peso_kg']-cancel['peso_kg'],1),'kg','Todas datas de coleta; novo tardio menos cancelamento futuro')
writecsv(E/'controles_referencia.csv',controls)
agg=defaultdict(lambda: [0,0,0,0])
for o in future:
    if o['status']=='CONFIRMADO':
        a=agg[(o['data_coleta'],o['rota_id'])];a[0]+=o['peso_kg'];a[1]+=o['volume_m3'];a[2]+=o['paletes'];a[3]+=1
writecsv(E/'holdout/alvo_diario.csv',[dict(data=d.isoformat(),rota_id=r['rota_id'],peso_kg=round(agg[(d.isoformat(),r['rota_id'])][0],1),volume_m3=round(agg[(d.isoformat(),r['rota_id'])][1],2),paletes=agg[(d.isoformat(),r['rota_id'])][2],pedidos=agg[(d.isoformat(),r['rota_id'])][3]) for d in days(CUT+timedelta(days=1),END) for r in data['rotas']])
md(E/'LEIA_PRIMEIRO_AVALIADOR.md',f'''# Material reservado ao avaliador

Nao entregar esta pasta nem o ZIP completo ao candidato. Enviar somente candidato.zip. Todos os dados sao sinteticos, seed 27102026, versao do pacote 1.0. O gerador nao e fornecido ao candidato; nao ha pipeline pronto ou solucao de referencia implementada.

## Aplicacao
1. Entregue briefing, contratos, criterios e base; mantenha o incremental fechado ate congelar previsao.
2. Registre o hash da entrega/previsao, data_corte e momento de recebimento.
3. Libere fase incremental e aplique duas vezes. O pedido {cancel['pedido_id']} passa de CONFIRMADO v1 para CANCELADO v2; P9000001 e novo e tardio. A segunda aplicacao nao altera totais. Carteira confirmada cai {cancel['peso_kg']} kg; historico confirmado sobe {late['peso_kg']} kg. O alvo holdout permanece fotografia original para a previsao original.
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
''')

md(C/'LEIA_PRIMEIRO.md', '''# Simulacao ViaTres Logistica

Comece por documentacao/01_BRIEFING_CEO.md e 02_DESAFIO_E_EXECUCAO.md. Leia os contratos, KPIs e aceite antes de implementar. Todos os dados sao ficticios e foram criados para avaliacao tecnica.

Base: 01/01/2025 a 27/09/2026. Corte de conhecimento: 27/09/2026 23:59:59, America/Sao_Paulo. Horizonte: 28/09 a 04/10/2026. O relogio do exercicio e fixo, independente da data atual.

- dados/base/: fontes CSV completas. Nao juntar XLSX como uma segunda fonte.
- planilhas_operacionais.xlsx: copia das previsoes manuais, cadastros e tarifas para inspecao humana; nao contem todo o historico volumoso.
- dados/incremental/: lote posterior, liberado apenas depois de congelar previsao.
- documentacao/: briefing, guia, dicionario por campo, KPIs, cenarios e rubrica.

Falhas de qualidade fazem parte do desafio. Nao existe sistema pronto neste pacote. O candidato deve criar a solucao; os documentos estabelecem escopo e evidencias esperadas. CSVs sao a fonte autoritativa. O XLSX preserva erros manuais, sem marca-los individualmente.
''')
md(PKG/'LEIA_PRIMEIRO.md', '''# Pacote completo de avaliacao — ViaTres

Este pacote tem duas audiencias. Entregue somente candidato.zip ao desenvolvedor. avaliador_RESTRITO inclui verdade sintetica, manifesto de defeitos, controles e resultados futuros; compartilhar antes da entrega invalida a avaliacao cega.

Arquivos CSV usam UTF-8 com BOM, separador ; e decimal ponto. Documentacao em Markdown abre em editor de texto ou visualizador Markdown. XLSX facilita inspecao das planilhas manuais e cadastros. Nada contem dados reais ou implementacao do sistema candidato.

Veja verificacao_pacote.json para testes executados e MANIFESTO_SHA256.csv para integridade. A referencia limpa e material de auditoria, nao uma solucao obrigatoria de limpeza.
''')

# Workbook payload only source copies, no analytics implementation.
payload={name:data[name] for name in ['previsao_manual','galpoes','rotas','frota','tarifas']}
(ROOT/'work/workbook_data.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')

# Verify coherent canonical world independently of injected issues.
tripmap={t['viagem_id']:t for t in clean['viagens']}; ordermap={o['pedido_id']:o for o in clean['pedidos']}
loads=defaultdict(lambda:[0,0,0]); seen=Counter(); ownkeys=[]
for x in clean['viagem_pedidos']:
    assert x['pedido_id'] in ordermap and x['viagem_id'] in tripmap
    assert ordermap[x['pedido_id']]['rota_id']==tripmap[x['viagem_id']]['rota_id']
    seen[x['pedido_id']]+=1
    a=loads[x['viagem_id']]
    for i,k in enumerate(['peso_embarcado_kg','volume_embarcado_m3','paletes_embarcados']): a[i]+=x[k]
for t in clean['viagens']:
    assert all(v<=cap+1e-7 for v,cap in zip(loads[t['viagem_id']],[t['cap_kg'],t['cap_m3'],t['cap_paletes']]))
    if t['modalidade']=='PROPRIO':
        key=(date.fromisoformat(t['data_saida']),t['veiculo_id']);ownkeys.append(key)
        assert avail[key]>=t['horas_ciclo']
assert len(set(ownkeys))==len(ownkeys)
assert all(seen[x['pedido_id']]==1 for x in hist)
assert abs(sum(x['peso_embarcado_kg'] for x in links)-sum(x['peso_kg'] for x in hist))<.01
assert all(o['atualizado_em']<=ASOF for o in clean['pedidos'])
assert all(x['data_entrega']=='' or x['data_entrega']<=CUT.isoformat() for x in clean['entregas'])
assert all(x['viagem_id'] in tripmap for x in clean['custos'])
assert len(dictrows)==sum(len(x[0]) for x in data.values())
checks=dict(status='APROVADO',seed=27102026,versao='1.0',pedidos_base_bruta=len(data['pedidos']),pedidos_historicos_confirmados=len(hist),viagens=len(trips),ocorrencias_manifesto=len(issues),campos_documentados=len(dictrows),tabelas_base=len(data),periodo_historico=[START.isoformat(),CUT.isoformat()],horizonte=[(CUT+timedelta(days=1)).isoformat(),END.isoformat()],testes=['FKs na referencia canonica','demanda historica = carga embarcada','uma alocacao por pedido historico confirmado','carga por viagem dentro de kg/m3/paletes','veiculo proprio nao duplicado por dia','horas de ciclo dentro da disponibilidade','nenhuma entrega realizada apos corte','pedidos-base conhecidos no corte','custos com viagem existente antes das falhas','dicionario cobre todos os campos'],limites=['Anomalias brutas sao intencionais','XLSX e copia parcial de fontes; historico completo em CSV','Nao ha teste de sistema candidato ou integracao real'])
(ROOT/'work/checks.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False))

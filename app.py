from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
from datetime import datetime, date
import calendar
import os

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'dennis_boxe.db'))
FRONTEND = os.path.join(BASE_DIR, 'frontend')


# ── helpers ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def add_months(dt, months):
    m = dt.month - 1 + months
    y = dt.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(dt.day, calendar.monthrange(y, m)[1]))

def calc_proximo(ultimo_str, tipo_plano):
    if not ultimo_str: return None
    try: dt = datetime.strptime(ultimo_str, '%Y-%m-%d').date()
    except: return None
    tipo = (tipo_plano or '').lower()
    return add_months(dt, 6 if 'semestral' in tipo else 3 if 'trimestral' in tipo else 1)

def calc_payment_valor(valor_mensal, tipo_plano):
    v = float(valor_mensal or 0)
    tipo = (tipo_plano or '').lower()
    return v * (6 if 'semestral' in tipo else 3 if 'trimestral' in tipo else 1)

def payment_status(proximo_str):
    if not proximo_str: return 'indefinido'
    try:
        delta = (datetime.strptime(proximo_str, '%Y-%m-%d').date() - date.today()).days
        if delta < 0:   return 'vencido'
        if delta == 0:  return 'vence_hoje'
        if delta <= 7:  return 'vence_breve'
        return 'em_dia'
    except: return 'indefinido'

STATUS_LABEL = {'vencido':'Vencido','vence_hoje':'Vence hoje','vence_breve':'Vence em breve','em_dia':'Em dia','indefinido':'Indefinido'}

def enrich_aluno(a):
    a = dict(a)
    if not a.get('proximo_pagamento') and a.get('ultimo_pagamento'):
        prox = calc_proximo(a['ultimo_pagamento'], a['tipo_plano'])
        if prox: a['proximo_pagamento'] = prox.strftime('%Y-%m-%d')
    a['status'] = payment_status(a.get('proximo_pagamento'))
    a['status_label'] = STATUS_LABEL.get(a['status'], a['status'])
    return a

MONTH_NAMES = {'01':'Jan','02':'Fev','03':'Mar','04':'Abr','05':'Mai','06':'Jun',
               '07':'Jul','08':'Ago','09':'Set','10':'Out','11':'Nov','12':'Dez'}

def last_n_months(n=6):
    today = date.today()
    out = []
    for i in range(n-1, -1, -1):
        m, y = today.month - i, today.year
        while m <= 0: m += 12; y -= 1
        out.append(f"{y}-{m:02d}")
    return out


# ── database ───────────────────────────────────────────────────────────────

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.executescript('''
        CREATE TABLE IF NOT EXISTS planos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE,
            preco REAL NOT NULL, valor_aula REAL, ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL,
            plano_nome TEXT, valor_mensal REAL, tipo_plano TEXT DEFAULT 'Mensal',
            ultimo_pagamento TEXT, proximo_pagamento TEXT, horarios TEXT,
            frequencia_semana REAL, sistema_pagamento TEXT DEFAULT 'PIX',
            observacoes TEXT, ativo INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT NOT NULL,
            valor REAL NOT NULL, data TEXT NOT NULL, categoria TEXT DEFAULT 'Outros',
            observacoes TEXT);
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, aluno_id INTEGER NOT NULL,
            aluno_nome TEXT NOT NULL, valor REAL NOT NULL, data TEXT NOT NULL,
            confirmado INTEGER DEFAULT 1, observacoes TEXT);
    ''')
    if cur.execute('SELECT COUNT(*) FROM planos').fetchone()[0] == 0:
        cur.executemany('INSERT INTO planos (nome,preco,valor_aula) VALUES(?,?,?)',[
            ('Boxe Coletivo 3x',120.0,25.0),('Boxe Coletivo 2x',80.0,None),
            ('Boxe Coletivo 1x',40.0,None),('Boxe Personal 1x',85.0,None),
            ('Boxe Personal 2x',165.0,None),('Boxe Personal 3x',250.0,None)])
    if cur.execute('SELECT COUNT(*) FROM alunos').fetchone()[0] == 0:
        cur.executemany('''INSERT INTO alunos(nome,plano_nome,valor_mensal,tipo_plano,
            ultimo_pagamento,proximo_pagamento,horarios,frequencia_semana,sistema_pagamento,observacoes)
            VALUES(?,?,?,?,?,?,?,?,?,?)''',[
            ('Victor Gallo','Boxe Personal 3x',250.0,'Mensal','2026-05-10','2026-06-10',None,5.0,'PIX',None),
            ('Júlio Laranjo','Boxe Coletivo 3x',120.0,'Trimestral','2026-05-07','2026-08-07','19:00 (Seg) e 19:00 (Qui)',2.0,'PIX','Renovação em Agosto'),
            ('Adriano Belux','Boxe Coletivo 2x',80.0,'Mensal','2026-04-25','2026-05-25','08:00 - 09:00 (Seg à Sex)',4.0,'PIX',None),
            ('Ricardo Rodrigues','Boxe Coletivo 3x',120.0,'Mensal','2026-05-09','2026-06-09',None,2.0,'PIX',None),
            ('Fernanda Victoria','Boxe Coletivo 3x',120.0,'Mensal','2026-05-04',None,None,3.0,'PIX',None),
            ('Samir Frade','Boxe Coletivo 3x',120.0,'Mensal','2026-04-16',None,None,3.0,'PIX',None),
            ('Ricardo Ferraz','Boxe Personal 1x',85.0,'Trimestral','2026-05-08',None,None,3.0,'PIX','Plano trimestral'),
            ('Diogo Godoi','Boxe Personal 3x',250.0,'Mensal','2026-04-17',None,None,1.0,'PIX',None),
            ('Marcelo Renan','Boxe Coletivo 3x',120.0,'Semestral',None,None,None,None,'PIX',None),
            ('Edneia Crescencio','Boxe Coletivo 3x',120.0,'Mensal','2026-05-17',None,None,None,'PIX',None),
            ('Ana Vitoria Teixeira','Boxe Coletivo 3x',120.0,'Mensal','2025-10-14',None,None,None,'PIX',None),
            ('Elizabete Aparecida Silva','Boxe Coletivo 3x',120.0,'Mensal','2026-04-17',None,None,None,'PIX',None),
            ('Priscila Maria','Boxe Coletivo 3x',120.0,'Mensal','2026-04-20',None,None,None,'PIX',None),
            ('Suelen Cristina','Boxe Coletivo 3x',120.0,'Mensal','2026-05-09',None,None,None,'PIX',None),
            ('Jaqueline Cristina','Boxe Coletivo 3x',120.0,'Mensal','2026-05-09',None,None,None,'PIX',None),
            ('Francisco Netto','Boxe Coletivo 3x',120.0,'Mensal','2026-05-11',None,None,None,None,None),
            ('Tiago Vargas','Boxe Coletivo 3x',120.0,'Mensal','2026-05-04',None,None,None,None,None),
            ('Eduardo','Boxe Personal 2x',165.0,'Mensal','2026-04-20',None,None,None,None,None),
            ('Gabriel','Boxe Coletivo 3x',120.0,'Mensal','2026-04-11',None,None,None,None,None)])
    if cur.execute('SELECT COUNT(*) FROM pagamentos').fetchone()[0] == 0:
        for r in cur.execute('SELECT id,nome,valor_mensal,tipo_plano,ultimo_pagamento FROM alunos WHERE ultimo_pagamento IS NOT NULL').fetchall():
            cur.execute('INSERT INTO pagamentos(aluno_id,aluno_nome,valor,data,confirmado) VALUES(?,?,?,?,1)',
                        (r[0],r[1],calc_payment_valor(r[2],r[3]),r[4]))
    conn.commit(); conn.close()


# ── API: dashboard ──────────────────────────────────────────────────────────

@app.route('/api/dashboard')
def api_dashboard():
    conn = get_db()
    alunos = [enrich_aluno(a) for a in conn.execute('SELECT * FROM alunos WHERE ativo=1 ORDER BY nome').fetchall()]
    hoje = date.today()
    mes = f"{hoje.year}-{hoje.month:02d}"
    confirmado = conn.execute("SELECT COALESCE(SUM(valor),0) FROM pagamentos WHERE strftime('%Y-%m',data)=? AND confirmado=1",(mes,)).fetchone()[0]
    despesas   = conn.execute("SELECT COALESCE(SUM(valor),0) FROM despesas WHERE strftime('%Y-%m',data)=?",(mes,)).fetchone()[0]
    conn.close()
    return jsonify({
        'total_alunos': len(alunos),
        'receita_mensal': sum(a['valor_mensal'] or 0 for a in alunos),
        'confirmado_mes': confirmado,
        'despesas_mes': despesas,
        'saldo': confirmado - despesas,
        'vencidos':    [a for a in alunos if a['status'] == 'vencido'],
        'vence_breve': [a for a in alunos if a['status'] in ('vence_hoje','vence_breve')],
        'hoje': hoje.isoformat(),
    })


# ── API: alunos ─────────────────────────────────────────────────────────────

@app.route('/api/alunos', methods=['GET'])
def api_alunos():
    conn = get_db()
    busca = request.args.get('busca','').strip()
    rows = conn.execute(
        'SELECT * FROM alunos WHERE ativo=1' + (' AND nome LIKE ?' if busca else '') + ' ORDER BY nome',
        ([f'%{busca}%'] if busca else [])).fetchall()
    conn.close()
    alunos = [enrich_aluno(a) for a in rows]
    sf = request.args.get('status','')
    if sf: alunos = [a for a in alunos if a['status'] == sf]
    return jsonify(alunos)

@app.route('/api/alunos/<int:id>', methods=['GET'])
def api_aluno(id):
    conn = get_db()
    a = conn.execute('SELECT * FROM alunos WHERE id=?',(id,)).fetchone()
    conn.close()
    return (jsonify(enrich_aluno(a)) if a else (jsonify({'error':'Não encontrado'}),404))

def _aluno_from_json(data):
    ultimo  = data.get('ultimo_pagamento') or None
    tipo    = data.get('tipo_plano','Mensal')
    proximo = data.get('proximo_pagamento') or None
    if not proximo and ultimo:
        prox = calc_proximo(ultimo, tipo)
        proximo = prox.strftime('%Y-%m-%d') if prox else None
    freq = data.get('frequencia_semana')
    return (data['nome'].strip(), data.get('plano_nome','').strip(),
            float(data.get('valor_mensal') or 0), tipo, ultimo, proximo,
            data.get('horarios','').strip() or None,
            float(freq) if freq else None,
            data.get('sistema_pagamento','PIX'),
            data.get('observacoes','').strip() or None)

@app.route('/api/alunos', methods=['POST'])
def api_aluno_novo():
    conn = get_db()
    cur = conn.execute('''INSERT INTO alunos(nome,plano_nome,valor_mensal,tipo_plano,
        ultimo_pagamento,proximo_pagamento,horarios,frequencia_semana,sistema_pagamento,observacoes)
        VALUES(?,?,?,?,?,?,?,?,?,?)''', _aluno_from_json(request.get_json()))
    conn.commit(); new_id = cur.lastrowid; conn.close()
    return jsonify({'ok':True,'id':new_id})

@app.route('/api/alunos/<int:id>', methods=['PUT'])
def api_aluno_editar(id):
    conn = get_db()
    vals = _aluno_from_json(request.get_json()) + (id,)
    conn.execute('''UPDATE alunos SET nome=?,plano_nome=?,valor_mensal=?,tipo_plano=?,
        ultimo_pagamento=?,proximo_pagamento=?,horarios=?,frequencia_semana=?,
        sistema_pagamento=?,observacoes=? WHERE id=?''', vals)
    conn.commit(); conn.close()
    return jsonify({'ok':True})

@app.route('/api/alunos/<int:id>', methods=['DELETE'])
def api_aluno_deletar(id):
    conn = get_db()
    conn.execute('UPDATE alunos SET ativo=0 WHERE id=?',(id,))
    conn.commit(); conn.close()
    return jsonify({'ok':True})

@app.route('/api/alunos/<int:id>/pagar', methods=['POST'])
def api_aluno_pagar(id):
    conn = get_db()
    a = dict(conn.execute('SELECT * FROM alunos WHERE id=?',(id,)).fetchone())
    hoje = date.today().strftime('%Y-%m-%d')
    prox = calc_proximo(hoje, a['tipo_plano'])
    conn.execute('UPDATE alunos SET ultimo_pagamento=?,proximo_pagamento=? WHERE id=?',
                 (hoje, prox.strftime('%Y-%m-%d') if prox else None, id))
    conn.execute('INSERT INTO pagamentos(aluno_id,aluno_nome,valor,data,confirmado) VALUES(?,?,?,?,1)',
                 (id, a['nome'], calc_payment_valor(a['valor_mensal'], a['tipo_plano']), hoje))
    conn.commit(); conn.close()
    return jsonify({'ok':True,'message':f'Pagamento de {a["nome"]} confirmado.'})


# ── API: planos ─────────────────────────────────────────────────────────────

@app.route('/api/planos', methods=['GET'])
def api_planos():
    conn = get_db()
    planos = [dict(p) for p in conn.execute('SELECT * FROM planos WHERE ativo=1 ORDER BY preco').fetchall()]
    conn.close(); return jsonify(planos)

@app.route('/api/planos', methods=['POST'])
def api_plano_novo():
    d = request.get_json(); conn = get_db()
    try:
        cur = conn.execute('INSERT INTO planos(nome,preco,valor_aula) VALUES(?,?,?)',(
            d['nome'].strip(), float(d.get('preco') or 0),
            float(d['valor_aula']) if d.get('valor_aula') else None))
        conn.commit(); nid = cur.lastrowid; conn.close()
        return jsonify({'ok':True,'id':nid})
    except Exception:
        conn.close(); return jsonify({'error':'Já existe um plano com esse nome.'}),400

@app.route('/api/planos/<int:id>', methods=['PUT'])
def api_plano_editar(id):
    d = request.get_json(); conn = get_db()
    conn.execute('UPDATE planos SET nome=?,preco=?,valor_aula=? WHERE id=?',(
        d['nome'].strip(), float(d.get('preco') or 0),
        float(d['valor_aula']) if d.get('valor_aula') else None, id))
    conn.commit(); conn.close(); return jsonify({'ok':True})

@app.route('/api/planos/<int:id>', methods=['DELETE'])
def api_plano_deletar(id):
    conn = get_db()
    conn.execute('UPDATE planos SET ativo=0 WHERE id=?',(id,))
    conn.commit(); conn.close(); return jsonify({'ok':True})


# ── API: financeiro ─────────────────────────────────────────────────────────

@app.route('/api/financeiro')
def api_financeiro():
    conn = get_db()
    hoje = date.today()
    mes  = request.args.get('mes', f"{hoje.year}-{hoje.month:02d}")
    confirmado = conn.execute("SELECT COALESCE(SUM(valor),0) FROM pagamentos WHERE strftime('%Y-%m',data)=? AND confirmado=1",(mes,)).fetchone()[0]
    despesas   = [dict(d) for d in conn.execute("SELECT * FROM despesas WHERE strftime('%Y-%m',data)=? ORDER BY data DESC",(mes,)).fetchall()]
    total_desp = sum(d['valor'] for d in despesas)
    pagamentos = [dict(p) for p in conn.execute(
        "SELECT p.*,a.plano_nome,a.tipo_plano FROM pagamentos p LEFT JOIN alunos a ON a.id=p.aluno_id WHERE strftime('%Y-%m',p.data)=? AND p.confirmado=1 ORDER BY p.data DESC",
        (mes,)).fetchall()]
    por_mes = []
    for m in last_n_months(6):
        rec  = conn.execute("SELECT COALESCE(SUM(valor),0) FROM pagamentos WHERE strftime('%Y-%m',data)=? AND confirmado=1",(m,)).fetchone()[0]
        desp = conn.execute("SELECT COALESCE(SUM(valor),0) FROM despesas WHERE strftime('%Y-%m',data)=?",(m,)).fetchone()[0]
        y,mm = m.split('-')
        por_mes.append({'mes':m,'label':f"{MONTH_NAMES[mm]}/{y}",'receita':rec,'despesas':desp,'saldo':rec-desp,'atual':m==f"{hoje.year}-{hoje.month:02d}"})
    conn.close()
    return jsonify({'confirmado_mes':confirmado,'total_despesas':total_desp,'saldo':confirmado-total_desp,
                    'despesas':despesas,'pagamentos_mes':pagamentos,'receita_por_mes':por_mes,'mes':mes})

@app.route('/api/despesas', methods=['POST'])
def api_despesa_nova():
    d = request.get_json(); conn = get_db()
    conn.execute('INSERT INTO despesas(descricao,valor,data,categoria,observacoes) VALUES(?,?,?,?,?)',(
        d['descricao'].strip(), float(d['valor']), d['data'],
        d.get('categoria','Outros'), d.get('observacoes','').strip() or None))
    conn.commit(); conn.close(); return jsonify({'ok':True})

@app.route('/api/despesas/<int:id>', methods=['DELETE'])
def api_despesa_deletar(id):
    conn = get_db()
    conn.execute('DELETE FROM despesas WHERE id=?',(id,))
    conn.commit(); conn.close(); return jsonify({'ok':True})


# ── serve frontend ──────────────────────────────────────────────────────────

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_frontend(path):
    full = os.path.join(FRONTEND, path)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND, path)
    if os.path.isfile(full + '.html'):
        return send_from_directory(FRONTEND, path + '.html')
    return send_from_directory(FRONTEND, 'index.html')


init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(debug=True, host='0.0.0.0', port=port)

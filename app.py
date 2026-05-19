from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, date
import calendar, os, re, sqlite3

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'dennis_boxe.db'))
FRONTEND = os.path.join(BASE_DIR, 'frontend')
USE_PG   = bool(os.environ.get('DATABASE_URL'))


# ── db helpers ──────────────────────────────────────────────────────────────

def get_db():
    if USE_PG:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
    return conn

def Q(query):
    """Adapt SQLite query syntax to PostgreSQL when needed."""
    if not USE_PG:
        return query
    q = query.replace('?', '%s')
    q = q.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    q = re.sub(r"strftime\('%Y-%m',\s*([^)]+?)\)",
               lambda m: f"to_char(({m.group(1).strip()})::date, 'YYYY-MM')", q)
    return q

def db_exec(conn, query, params=()):
    cur = conn.cursor()
    cur.execute(Q(query), list(params) if params else [])
    return cur

def db_all(conn, query, params=()):
    return list(db_exec(conn, query, params).fetchall())

def db_one(conn, query, params=()):
    return db_exec(conn, query, params).fetchone()

def db_val(conn, query, params=()):
    row = db_one(conn, query, params)
    return list(row.values())[0] if row else None

def db_insert(conn, query, params):
    cur = conn.cursor()
    if USE_PG:
        cur.execute(Q(query) + ' RETURNING id', list(params))
        return cur.fetchone()['id']
    cur.execute(Q(query), params)
    return cur.lastrowid


# ── business logic ──────────────────────────────────────────────────────────

def add_months(dt, months):
    m = dt.month - 1 + months
    y = dt.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(dt.day, calendar.monthrange(y, m)[1]))

def calc_proximo(ultimo_str, tipo_plano):
    if not ultimo_str: return None
    try: dt = datetime.strptime(str(ultimo_str)[:10], '%Y-%m-%d').date()
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
        delta = (datetime.strptime(str(proximo_str)[:10], '%Y-%m-%d').date() - date.today()).days
        if delta < 0:  return 'vencido'
        if delta == 0: return 'vence_hoje'
        if delta <= 7: return 'vence_breve'
        return 'em_dia'
    except: return 'indefinido'

STATUS_LABEL = {'vencido':'Vencido','vence_hoje':'Vence hoje',
                'vence_breve':'Vence em breve','em_dia':'Em dia','indefinido':'Indefinido'}

def enrich_aluno(a):
    a = dict(a)
    if not a.get('proximo_pagamento') and a.get('ultimo_pagamento'):
        prox = calc_proximo(a['ultimo_pagamento'], a['tipo_plano'])
        if prox: a['proximo_pagamento'] = prox.strftime('%Y-%m-%d')
    a['status']       = payment_status(a.get('proximo_pagamento'))
    a['status_label'] = STATUS_LABEL.get(a['status'], a['status'])
    # ensure JSON-serialisable dates
    for k in ('ultimo_pagamento', 'proximo_pagamento'):
        if a.get(k): a[k] = str(a[k])[:10]
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


# ── init db ─────────────────────────────────────────────────────────────────

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS planos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        preco REAL NOT NULL,
        valor_aula REAL,
        ativo INTEGER DEFAULT 1)""",
    """CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        plano_nome TEXT,
        valor_mensal REAL,
        tipo_plano TEXT DEFAULT 'Mensal',
        ultimo_pagamento TEXT,
        proximo_pagamento TEXT,
        horarios TEXT,
        frequencia_semana REAL,
        sistema_pagamento TEXT DEFAULT 'PIX',
        observacoes TEXT,
        ativo INTEGER DEFAULT 1)""",
    """CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        data TEXT NOT NULL,
        categoria TEXT DEFAULT 'Outros',
        observacoes TEXT)""",
    """CREATE TABLE IF NOT EXISTS pagamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aluno_id INTEGER NOT NULL,
        aluno_nome TEXT NOT NULL,
        valor REAL NOT NULL,
        data TEXT NOT NULL,
        confirmado INTEGER DEFAULT 1,
        observacoes TEXT)""",
]

SEED_PLANOS = [
    ('Boxe Coletivo 3x',120.0,25.0),('Boxe Coletivo 2x',80.0,None),
    ('Boxe Coletivo 1x',40.0,None),('Boxe Personal 1x',85.0,None),
    ('Boxe Personal 2x',165.0,None),('Boxe Personal 3x',250.0,None),
]

SEED_ALUNOS = [
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
    ('Gabriel','Boxe Coletivo 3x',120.0,'Mensal','2026-04-11',None,None,None,None,None),
]

def init_db():
    conn = get_db()
    for s in SCHEMA:
        db_exec(conn, s)

    if db_val(conn, 'SELECT COUNT(*) AS c FROM planos') == 0:
        for row in SEED_PLANOS:
            db_exec(conn, 'INSERT INTO planos(nome,preco,valor_aula) VALUES(?,?,?)', row)

    if db_val(conn, 'SELECT COUNT(*) AS c FROM alunos') == 0:
        for row in SEED_ALUNOS:
            db_exec(conn, '''INSERT INTO alunos(nome,plano_nome,valor_mensal,tipo_plano,
                ultimo_pagamento,proximo_pagamento,horarios,frequencia_semana,
                sistema_pagamento,observacoes) VALUES(?,?,?,?,?,?,?,?,?,?)''', row)

    if db_val(conn, 'SELECT COUNT(*) AS c FROM pagamentos') == 0:
        for r in db_all(conn, 'SELECT id,nome,valor_mensal,tipo_plano,ultimo_pagamento FROM alunos WHERE ultimo_pagamento IS NOT NULL'):
            db_exec(conn,
                'INSERT INTO pagamentos(aluno_id,aluno_nome,valor,data,confirmado) VALUES(?,?,?,?,1)',
                (r['id'], r['nome'], calc_payment_valor(r['valor_mensal'], r['tipo_plano']), r['ultimo_pagamento']))

    conn.commit()
    conn.close()


# ── API: dashboard ──────────────────────────────────────────────────────────

@app.route('/api/dashboard')
def api_dashboard():
    conn = get_db()
    alunos = [enrich_aluno(a) for a in db_all(conn, 'SELECT * FROM alunos WHERE ativo=1 ORDER BY nome')]
    hoje = date.today()
    mes  = f"{hoje.year}-{hoje.month:02d}"
    confirmado = db_val(conn, "SELECT COALESCE(SUM(valor),0) AS v FROM pagamentos WHERE strftime('%Y-%m',data)=? AND confirmado=1", [mes])
    despesas   = db_val(conn, "SELECT COALESCE(SUM(valor),0) AS v FROM despesas WHERE strftime('%Y-%m',data)=?", [mes])
    conn.close()
    return jsonify({
        'total_alunos':  len(alunos),
        'receita_mensal': sum(a['valor_mensal'] or 0 for a in alunos),
        'confirmado_mes': float(confirmado or 0),
        'despesas_mes':   float(despesas or 0),
        'saldo':          float(confirmado or 0) - float(despesas or 0),
        'vencidos':       [a for a in alunos if a['status'] == 'vencido'],
        'vence_breve':    [a for a in alunos if a['status'] in ('vence_hoje','vence_breve')],
        'hoje':           hoje.isoformat(),
    })


# ── API: alunos ─────────────────────────────────────────────────────────────

@app.route('/api/alunos', methods=['GET'])
def api_alunos():
    conn = get_db()
    busca = request.args.get('busca','').strip()
    rows  = db_all(conn,
        'SELECT * FROM alunos WHERE ativo=1' + (' AND nome LIKE ?' if busca else '') + ' ORDER BY nome',
        ([f'%{busca}%'] if busca else []))
    conn.close()
    alunos = [enrich_aluno(a) for a in rows]
    sf = request.args.get('status','')
    if sf: alunos = [a for a in alunos if a['status'] == sf]
    return jsonify(alunos)

@app.route('/api/alunos/<int:id>', methods=['GET'])
def api_aluno(id):
    conn = get_db()
    a = db_one(conn, 'SELECT * FROM alunos WHERE id=?', [id])
    conn.close()
    return jsonify(enrich_aluno(a)) if a else (jsonify({'error':'Não encontrado'}), 404)

def _aluno_tuple(data):
    ultimo  = data.get('ultimo_pagamento') or None
    tipo    = data.get('tipo_plano') or 'Mensal'
    proximo = data.get('proximo_pagamento') or None
    if not proximo and ultimo:
        prox = calc_proximo(ultimo, tipo)
        proximo = prox.strftime('%Y-%m-%d') if prox else None
    freq = data.get('frequencia_semana')
    return (
        (data.get('nome') or '').strip(),
        (data.get('plano_nome') or '').strip(),
        float(data.get('valor_mensal') or 0),
        tipo, ultimo, proximo,
        (data.get('horarios') or '').strip() or None,
        float(freq) if freq else None,
        data.get('sistema_pagamento') or 'PIX',
        (data.get('observacoes') or '').strip() or None,
    )

@app.route('/api/alunos', methods=['POST'])
def api_aluno_novo():
    conn = get_db()
    new_id = db_insert(conn, '''INSERT INTO alunos(nome,plano_nome,valor_mensal,tipo_plano,
        ultimo_pagamento,proximo_pagamento,horarios,frequencia_semana,
        sistema_pagamento,observacoes) VALUES(?,?,?,?,?,?,?,?,?,?)''',
        _aluno_tuple(request.get_json()))
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'id': new_id})

@app.route('/api/alunos/<int:id>', methods=['PUT'])
def api_aluno_editar(id):
    conn = get_db()
    db_exec(conn, '''UPDATE alunos SET nome=?,plano_nome=?,valor_mensal=?,tipo_plano=?,
        ultimo_pagamento=?,proximo_pagamento=?,horarios=?,frequencia_semana=?,
        sistema_pagamento=?,observacoes=? WHERE id=?''',
        _aluno_tuple(request.get_json()) + (id,))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/alunos/<int:id>', methods=['DELETE'])
def api_aluno_deletar(id):
    conn = get_db()
    db_exec(conn, 'UPDATE alunos SET ativo=0 WHERE id=?', [id])
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/alunos/<int:id>/pagar', methods=['POST'])
def api_aluno_pagar(id):
    conn = get_db()
    a    = db_one(conn, 'SELECT * FROM alunos WHERE id=?', [id])
    hoje = date.today().strftime('%Y-%m-%d')
    prox = calc_proximo(hoje, a['tipo_plano'])
    db_exec(conn, 'UPDATE alunos SET ultimo_pagamento=?,proximo_pagamento=? WHERE id=?',
            [hoje, prox.strftime('%Y-%m-%d') if prox else None, id])
    db_exec(conn, 'INSERT INTO pagamentos(aluno_id,aluno_nome,valor,data,confirmado) VALUES(?,?,?,?,1)',
            [id, a['nome'], calc_payment_valor(a['valor_mensal'], a['tipo_plano']), hoje])
    conn.commit(); conn.close()
    return jsonify({'ok': True, 'message': f'Pagamento de {a["nome"]} confirmado.'})


# ── API: planos ─────────────────────────────────────────────────────────────

@app.route('/api/planos', methods=['GET'])
def api_planos():
    conn = get_db()
    rows = db_all(conn, 'SELECT * FROM planos WHERE ativo=1 ORDER BY preco')
    conn.close(); return jsonify(rows)

@app.route('/api/planos', methods=['POST'])
def api_plano_novo():
    d = request.get_json(); conn = get_db()
    try:
        new_id = db_insert(conn, 'INSERT INTO planos(nome,preco,valor_aula) VALUES(?,?,?)',
            [d['nome'].strip(), float(d.get('preco') or 0),
             float(d['valor_aula']) if d.get('valor_aula') else None])
        conn.commit(); conn.close()
        return jsonify({'ok': True, 'id': new_id})
    except Exception:
        conn.close(); return jsonify({'error': 'Já existe um plano com esse nome.'}), 400

@app.route('/api/planos/<int:id>', methods=['PUT'])
def api_plano_editar(id):
    d = request.get_json(); conn = get_db()
    db_exec(conn, 'UPDATE planos SET nome=?,preco=?,valor_aula=? WHERE id=?',
            [d['nome'].strip(), float(d.get('preco') or 0),
             float(d['valor_aula']) if d.get('valor_aula') else None, id])
    conn.commit(); conn.close(); return jsonify({'ok': True})

@app.route('/api/planos/<int:id>', methods=['DELETE'])
def api_plano_deletar(id):
    conn = get_db()
    db_exec(conn, 'UPDATE planos SET ativo=0 WHERE id=?', [id])
    conn.commit(); conn.close(); return jsonify({'ok': True})


# ── API: financeiro ─────────────────────────────────────────────────────────

@app.route('/api/financeiro')
def api_financeiro():
    conn = get_db()
    hoje = date.today()
    mes  = request.args.get('mes', f"{hoje.year}-{hoje.month:02d}")

    confirmado = db_val(conn,
        "SELECT COALESCE(SUM(valor),0) AS v FROM pagamentos WHERE strftime('%Y-%m',data)=? AND confirmado=1", [mes])
    despesas   = db_all(conn,
        "SELECT * FROM despesas WHERE strftime('%Y-%m',data)=? ORDER BY data DESC", [mes])
    total_desp = sum(float(d['valor']) for d in despesas)
    pagamentos = db_all(conn,
        "SELECT p.*,a.plano_nome,a.tipo_plano FROM pagamentos p LEFT JOIN alunos a ON a.id=p.aluno_id "
        "WHERE strftime('%Y-%m',p.data)=? AND p.confirmado=1 ORDER BY p.data DESC", [mes])

    por_mes = []
    for m in last_n_months(6):
        rec  = float(db_val(conn,"SELECT COALESCE(SUM(valor),0) AS v FROM pagamentos WHERE strftime('%Y-%m',data)=? AND confirmado=1",[m]) or 0)
        desp = float(db_val(conn,"SELECT COALESCE(SUM(valor),0) AS v FROM despesas WHERE strftime('%Y-%m',data)=?",[m]) or 0)
        y, mm = m.split('-')
        por_mes.append({'mes':m,'label':f"{MONTH_NAMES[mm]}/{y}",'receita':rec,
                        'despesas':desp,'saldo':rec-desp,'atual':m==f"{hoje.year}-{hoje.month:02d}"})

    # ensure dates are strings
    for p in pagamentos:
        p['data'] = str(p['data'])[:10]
    for d in despesas:
        d['data'] = str(d['data'])[:10]

    conn.close()
    return jsonify({'confirmado_mes':float(confirmado or 0),'total_despesas':total_desp,
                    'saldo':float(confirmado or 0)-total_desp,'despesas':despesas,
                    'pagamentos_mes':pagamentos,'receita_por_mes':por_mes,'mes':mes})

@app.route('/api/despesas', methods=['POST'])
def api_despesa_nova():
    d = request.get_json(); conn = get_db()
    db_exec(conn, 'INSERT INTO despesas(descricao,valor,data,categoria,observacoes) VALUES(?,?,?,?,?)',
            [d['descricao'].strip(), float(d['valor']), d['data'],
             d.get('categoria','Outros'), d.get('observacoes','').strip() or None])
    conn.commit(); conn.close(); return jsonify({'ok': True})

@app.route('/api/despesas/<int:id>', methods=['DELETE'])
def api_despesa_deletar(id):
    conn = get_db()
    db_exec(conn, 'DELETE FROM despesas WHERE id=?', [id])
    conn.commit(); conn.close(); return jsonify({'ok': True})


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'mode': 'postgres' if USE_PG else 'sqlite'})


# ── serve frontend (local only) ─────────────────────────────────────────────

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_frontend(path):
    # API paths must never be served as HTML
    if path.startswith('api') or path == 'health':
        return jsonify({'error': f'/{path} não encontrado'}), 404
    # On Railway, Flask is API-only
    if USE_PG:
        return jsonify({'error': f'/{path} não encontrado'}), 404
    full = os.path.join(FRONTEND, path)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND, path)
    if os.path.isfile(full + '.html'):
        return send_from_directory(FRONTEND, path + '.html')
    return send_from_directory(FRONTEND, 'index.html')


@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({'error': str(e)}), 500


init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(debug=True, host='0.0.0.0', port=port)

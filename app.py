from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, date
import calendar
import os

app = Flask(__name__)
app.secret_key = 'dennis-boxe-2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'dennis_boxe.db'))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def add_months(dt, months):
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calc_payment_valor(valor_mensal, tipo_plano):
    v = float(valor_mensal or 0)
    tipo = (tipo_plano or '').strip().lower()
    if 'semestral' in tipo:
        return v * 6
    elif 'trimestral' in tipo:
        return v * 3
    return v


def calc_proximo(ultimo_str, tipo_plano):
    if not ultimo_str:
        return None
    try:
        dt = datetime.strptime(ultimo_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None
    tipo = (tipo_plano or '').strip().lower()
    if 'semestral' in tipo:
        months = 6
    elif 'trimestral' in tipo:
        months = 3
    else:
        months = 1
    return add_months(dt, months)


def payment_status(proximo_str):
    if not proximo_str:
        return 'indefinido'
    try:
        proximo = datetime.strptime(proximo_str, '%Y-%m-%d').date()
        delta = (proximo - date.today()).days
        if delta < 0:
            return 'vencido'
        elif delta == 0:
            return 'vence_hoje'
        elif delta <= 7:
            return 'vence_breve'
        else:
            return 'em_dia'
    except (ValueError, TypeError):
        return 'indefinido'


STATUS_LABEL = {
    'vencido': 'Vencido',
    'vence_hoje': 'Vence hoje',
    'vence_breve': 'Vence em breve',
    'em_dia': 'Em dia',
    'indefinido': 'Indefinido',
}


def enrich_aluno(a):
    a = dict(a)
    if not a.get('proximo_pagamento') and a.get('ultimo_pagamento'):
        prox = calc_proximo(a['ultimo_pagamento'], a['tipo_plano'])
        if prox:
            a['proximo_pagamento'] = prox.strftime('%Y-%m-%d')
    a['status'] = payment_status(a.get('proximo_pagamento'))
    a['status_label'] = STATUS_LABEL.get(a['status'], a['status'])
    return a


@app.template_filter('datebr')
def datebr(value):
    if not value:
        return '—'
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
    except Exception:
        return value


@app.template_filter('brl')
def brl(value):
    if value is None:
        return '—'
    return f"R$ {float(value):,.0f}".replace(',', '.')


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript('''
        CREATE TABLE IF NOT EXISTS planos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            preco REAL NOT NULL,
            valor_aula REAL,
            ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS alunos (
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
            ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            data TEXT NOT NULL,
            categoria TEXT DEFAULT 'Outros',
            observacoes TEXT
        );
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            aluno_nome TEXT NOT NULL,
            valor REAL NOT NULL,
            data TEXT NOT NULL,
            confirmado INTEGER DEFAULT 1,
            observacoes TEXT
        );
    ''')
    if cur.execute('SELECT COUNT(*) FROM planos').fetchone()[0] == 0:
        cur.executemany('INSERT INTO planos (nome, preco, valor_aula) VALUES (?,?,?)', [
            ('Boxe Coletivo 3x', 120.0, 25.0),
            ('Boxe Coletivo 2x', 80.0, None),
            ('Boxe Coletivo 1x', 40.0, None),
            ('Boxe Personal 1x', 85.0, None),
            ('Boxe Personal 2x', 165.0, None),
            ('Boxe Personal 3x', 250.0, None),
        ])
    if cur.execute('SELECT COUNT(*) FROM alunos').fetchone()[0] == 0:
        cur.executemany('''
            INSERT INTO alunos (nome, plano_nome, valor_mensal, tipo_plano,
                ultimo_pagamento, proximo_pagamento, horarios, frequencia_semana,
                sistema_pagamento, observacoes)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        ''', [
            ('Victor Gallo', 'Boxe Personal 3x', 250.0, 'Mensal', '2026-05-10', '2026-06-10', None, 5.0, 'PIX', None),
            ('Júlio Laranjo', 'Boxe Coletivo 3x', 120.0, 'Trimestral', '2026-05-07', '2026-08-07', '19:00 (Seg) e 19:00 (Qui)', 2.0, 'PIX', 'Renovação em Agosto'),
            ('Adriano Belux', 'Boxe Coletivo 2x', 80.0, 'Mensal', '2026-04-25', '2026-05-25', '08:00 - 09:00 (Seg à Sex)', 4.0, 'PIX', None),
            ('Ricardo Rodrigues', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2026-05-09', '2026-06-09', None, 2.0, 'PIX', None),
            ('Fernanda Victoria', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2026-05-04', None, None, 3.0, 'PIX', None),
            ('Samir Frade', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2026-04-16', None, None, 3.0, 'PIX', None),
            ('Ricardo Ferraz', 'Boxe Personal 1x', 85.0, 'Trimestral', '2026-05-08', None, None, 3.0, 'PIX', 'Plano trimestral'),
            ('Diogo Godoi', 'Boxe Personal 3x', 250.0, 'Mensal', '2026-04-17', None, None, 1.0, 'PIX', None),
            ('Marcelo Renan', 'Boxe Coletivo 3x', 120.0, 'Semestral', None, None, None, None, 'PIX', None),
            ('Edneia Crescencio', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2026-05-17', None, None, None, 'PIX', None),
            ('Ana Vitoria Teixeira', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2025-10-14', None, None, None, 'PIX', None),
            ('Elizabete Aparecida Silva', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2026-04-17', None, None, None, 'PIX', None),
            ('Priscila Maria', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2026-04-20', None, None, None, 'PIX', None),
            ('Suelen Cristina', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2026-05-09', None, None, None, 'PIX', None),
            ('Jaqueline Cristina', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2026-05-09', None, None, None, 'PIX', None),
            ('Francisco Netto', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2026-05-11', None, None, None, None, None),
            ('Tiago Vargas', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2026-05-04', None, None, None, None, None),
            ('Eduardo', 'Boxe Personal 2x', 165.0, 'Mensal', '2026-04-20', None, None, None, None, None),
            ('Gabriel', 'Boxe Coletivo 3x', 120.0, 'Mensal', '2026-04-11', None, None, None, None, None),
        ])
    # Seed pagamentos from existing ultimo_pagamento (one-time migration)
    if cur.execute('SELECT COUNT(*) FROM pagamentos').fetchone()[0] == 0:
        rows = cur.execute(
            'SELECT id, nome, valor_mensal, tipo_plano, ultimo_pagamento FROM alunos WHERE ultimo_pagamento IS NOT NULL'
        ).fetchall()
        for r in rows:
            valor = calc_payment_valor(r[2], r[3])
            cur.execute(
                'INSERT INTO pagamentos (aluno_id, aluno_nome, valor, data, confirmado) VALUES (?,?,?,?,1)',
                (r[0], r[1], valor, r[4])
            )

    conn.commit()
    conn.close()


def last_n_months(n=6):
    today = date.today()
    months = []
    for i in range(n - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        months.append(f"{y}-{m:02d}")
    return months


MONTH_NAMES = {
    '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr',
    '05': 'Mai', '06': 'Jun', '07': 'Jul', '08': 'Ago',
    '09': 'Set', '10': 'Out', '11': 'Nov', '12': 'Dez',
}


# ── DASHBOARD ──────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    conn = get_db()
    alunos = [enrich_aluno(a) for a in conn.execute(
        'SELECT * FROM alunos WHERE ativo=1 ORDER BY nome').fetchall()]

    hoje = date.today()
    mes_atual = f"{hoje.year}-{hoje.month:02d}"

    total_alunos = len(alunos)
    receita_mensal = sum(a['valor_mensal'] or 0 for a in alunos)
    despesas_mes = conn.execute(
        "SELECT COALESCE(SUM(valor),0) FROM despesas WHERE strftime('%Y-%m',data)=?",
        (mes_atual,)).fetchone()[0]
    confirmado_mes = conn.execute(
        "SELECT COALESCE(SUM(valor),0) FROM pagamentos WHERE strftime('%Y-%m',data)=? AND confirmado=1",
        (mes_atual,)).fetchone()[0]
    saldo = confirmado_mes - despesas_mes

    vencidos = [a for a in alunos if a['status'] == 'vencido']
    vence_breve = [a for a in alunos if a['status'] in ('vence_hoje', 'vence_breve')]
    conn.close()

    return render_template('dashboard.html',
        total_alunos=total_alunos,
        receita_mensal=receita_mensal,
        confirmado_mes=confirmado_mes,
        despesas_mes=despesas_mes,
        saldo=saldo,
        vencidos=vencidos,
        vence_breve=vence_breve,
        hoje=hoje)


# ── ALUNOS ─────────────────────────────────────────────────────────────────

@app.route('/alunos')
def alunos():
    conn = get_db()
    busca = request.args.get('busca', '').strip()
    status_f = request.args.get('status', '')

    rows = conn.execute(
        'SELECT * FROM alunos WHERE ativo=1' +
        (' AND nome LIKE ?' if busca else '') +
        ' ORDER BY nome',
        ([f'%{busca}%'] if busca else [])
    ).fetchall()
    conn.close()

    alunos_list = [enrich_aluno(a) for a in rows]
    if status_f:
        alunos_list = [a for a in alunos_list if a['status'] == status_f]

    counts = {s: sum(1 for a in alunos_list if a['status'] == s)
              for s in ('vencido', 'vence_hoje', 'vence_breve', 'em_dia', 'indefinido')}

    return render_template('alunos.html',
        alunos=alunos_list, busca=busca,
        status_f=status_f, counts=counts)


@app.route('/alunos/novo', methods=['GET', 'POST'])
def aluno_novo():
    conn = get_db()
    planos = conn.execute('SELECT * FROM planos WHERE ativo=1 ORDER BY nome').fetchall()

    if request.method == 'POST':
        ultimo = request.form.get('ultimo_pagamento') or None
        tipo = request.form.get('tipo_plano', 'Mensal')
        proximo = request.form.get('proximo_pagamento') or None
        if not proximo and ultimo:
            prox = calc_proximo(ultimo, tipo)
            proximo = prox.strftime('%Y-%m-%d') if prox else None

        freq = request.form.get('frequencia_semana')
        conn.execute('''
            INSERT INTO alunos (nome, plano_nome, valor_mensal, tipo_plano,
                ultimo_pagamento, proximo_pagamento, horarios, frequencia_semana,
                sistema_pagamento, observacoes)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        ''', (
            request.form['nome'].strip(),
            request.form.get('plano_nome', '').strip(),
            float(request.form.get('valor_mensal') or 0),
            tipo, ultimo, proximo,
            request.form.get('horarios', '').strip() or None,
            float(freq) if freq else None,
            request.form.get('sistema_pagamento', 'PIX'),
            request.form.get('observacoes', '').strip() or None,
        ))
        conn.commit()
        conn.close()
        flash('Aluno adicionado com sucesso.')
        return redirect(url_for('alunos'))

    conn.close()
    return render_template('aluno_form.html', planos=planos, aluno=None)


@app.route('/alunos/<int:id>/editar', methods=['GET', 'POST'])
def aluno_editar(id):
    conn = get_db()
    aluno = conn.execute('SELECT * FROM alunos WHERE id=?', (id,)).fetchone()
    if not aluno:
        conn.close()
        flash('Aluno não encontrado.')
        return redirect(url_for('alunos'))

    planos = conn.execute('SELECT * FROM planos WHERE ativo=1 ORDER BY nome').fetchall()

    if request.method == 'POST':
        ultimo = request.form.get('ultimo_pagamento') or None
        tipo = request.form.get('tipo_plano', 'Mensal')
        proximo = request.form.get('proximo_pagamento') or None
        if not proximo and ultimo:
            prox = calc_proximo(ultimo, tipo)
            proximo = prox.strftime('%Y-%m-%d') if prox else None

        freq = request.form.get('frequencia_semana')
        conn.execute('''
            UPDATE alunos SET nome=?, plano_nome=?, valor_mensal=?, tipo_plano=?,
                ultimo_pagamento=?, proximo_pagamento=?, horarios=?, frequencia_semana=?,
                sistema_pagamento=?, observacoes=?
            WHERE id=?
        ''', (
            request.form['nome'].strip(),
            request.form.get('plano_nome', '').strip(),
            float(request.form.get('valor_mensal') or 0),
            tipo, ultimo, proximo,
            request.form.get('horarios', '').strip() or None,
            float(freq) if freq else None,
            request.form.get('sistema_pagamento', 'PIX'),
            request.form.get('observacoes', '').strip() or None,
            id,
        ))
        conn.commit()
        conn.close()
        flash('Aluno atualizado.')
        return redirect(url_for('alunos'))

    conn.close()
    return render_template('aluno_form.html', planos=planos, aluno=dict(aluno))


@app.route('/alunos/<int:id>/pagar', methods=['POST'])
def aluno_pagar(id):
    conn = get_db()
    aluno = dict(conn.execute('SELECT * FROM alunos WHERE id=?', (id,)).fetchone())
    hoje = date.today().strftime('%Y-%m-%d')
    prox = calc_proximo(hoje, aluno['tipo_plano'])
    proximo = prox.strftime('%Y-%m-%d') if prox else None
    valor = calc_payment_valor(aluno['valor_mensal'], aluno['tipo_plano'])
    conn.execute('UPDATE alunos SET ultimo_pagamento=?, proximo_pagamento=? WHERE id=?',
                 (hoje, proximo, id))
    conn.execute('INSERT INTO pagamentos (aluno_id, aluno_nome, valor, data, confirmado) VALUES (?,?,?,?,1)',
                 (id, aluno['nome'], valor, hoje))
    conn.commit()
    conn.close()
    flash(f'Pagamento de {aluno["nome"]} confirmado — {valor:.0f} R$.')
    return redirect(request.referrer or url_for('alunos'))


@app.route('/alunos/<int:id>/deletar', methods=['POST'])
def aluno_deletar(id):
    conn = get_db()
    conn.execute('UPDATE alunos SET ativo=0 WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Aluno removido.')
    return redirect(url_for('alunos'))


# ── PLANOS ─────────────────────────────────────────────────────────────────

@app.route('/planos')
def planos():
    conn = get_db()
    planos_list = conn.execute('SELECT * FROM planos WHERE ativo=1 ORDER BY preco').fetchall()
    conn.close()
    return render_template('planos.html', planos=planos_list)


@app.route('/planos/novo', methods=['POST'])
def plano_novo():
    conn = get_db()
    nome = request.form['nome'].strip()
    preco = float(request.form.get('preco') or 0)
    valor_aula = request.form.get('valor_aula')
    valor_aula = float(valor_aula) if valor_aula else None
    try:
        conn.execute('INSERT INTO planos (nome, preco, valor_aula) VALUES (?,?,?)',
                     (nome, preco, valor_aula))
        conn.commit()
        flash('Plano criado.')
    except Exception:
        flash('Já existe um plano com esse nome.')
    conn.close()
    return redirect(url_for('planos'))


@app.route('/planos/<int:id>/editar', methods=['POST'])
def plano_editar(id):
    conn = get_db()
    nome = request.form['nome'].strip()
    preco = float(request.form.get('preco') or 0)
    valor_aula = request.form.get('valor_aula')
    valor_aula = float(valor_aula) if valor_aula else None
    conn.execute('UPDATE planos SET nome=?, preco=?, valor_aula=? WHERE id=?',
                 (nome, preco, valor_aula, id))
    conn.commit()
    conn.close()
    flash('Plano atualizado.')
    return redirect(url_for('planos'))


@app.route('/planos/<int:id>/deletar', methods=['POST'])
def plano_deletar(id):
    conn = get_db()
    conn.execute('UPDATE planos SET ativo=0 WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Plano removido.')
    return redirect(url_for('planos'))


# ── FINANCEIRO ─────────────────────────────────────────────────────────────

@app.route('/financeiro')
def financeiro():
    conn = get_db()
    hoje = date.today()
    mes = request.args.get('mes', f"{hoje.year}-{hoje.month:02d}")

    # Receita confirmada do mês selecionado (pagamentos reais)
    confirmado_mes = conn.execute(
        "SELECT COALESCE(SUM(valor),0) FROM pagamentos WHERE strftime('%Y-%m',data)=? AND confirmado=1",
        (mes,)).fetchone()[0]

    # Despesas do mês selecionado
    despesas = conn.execute(
        "SELECT * FROM despesas WHERE strftime('%Y-%m',data)=? ORDER BY data DESC",
        (mes,)).fetchall()
    total_despesas = sum(d['valor'] for d in despesas)
    saldo = confirmado_mes - total_despesas

    # Pagamentos do mês selecionado
    pagamentos_mes = conn.execute(
        """SELECT p.*, a.plano_nome, a.tipo_plano FROM pagamentos p
           LEFT JOIN alunos a ON a.id = p.aluno_id
           WHERE strftime('%Y-%m', p.data)=? AND p.confirmado=1
           ORDER BY p.data DESC""",
        (mes,)).fetchall()

    # Tabela últimos 6 meses
    receita_por_mes = []
    for m in last_n_months(6):
        rec = conn.execute(
            "SELECT COALESCE(SUM(valor),0) FROM pagamentos WHERE strftime('%Y-%m',data)=? AND confirmado=1",
            (m,)).fetchone()[0]
        desp = conn.execute(
            "SELECT COALESCE(SUM(valor),0) FROM despesas WHERE strftime('%Y-%m',data)=?",
            (m,)).fetchone()[0]
        y, mm = m.split('-')
        receita_por_mes.append({
            'mes': m,
            'label': f"{MONTH_NAMES[mm]}/{y}",
            'receita': rec,
            'despesas': desp,
            'saldo': rec - desp,
            'atual': m == f"{hoje.year}-{hoje.month:02d}",
        })

    conn.close()
    return render_template('financeiro.html',
        confirmado_mes=confirmado_mes,
        total_despesas=total_despesas,
        saldo=saldo,
        despesas=despesas,
        pagamentos_mes=pagamentos_mes,
        receita_por_mes=receita_por_mes,
        mes=mes,
        hoje=hoje)


@app.route('/financeiro/despesas/nova', methods=['POST'])
def despesa_nova():
    conn = get_db()
    conn.execute('INSERT INTO despesas (descricao, valor, data, categoria, observacoes) VALUES (?,?,?,?,?)', (
        request.form['descricao'].strip(),
        float(request.form['valor']),
        request.form['data'],
        request.form.get('categoria', 'Outros'),
        request.form.get('observacoes', '').strip() or None,
    ))
    conn.commit()
    conn.close()
    flash('Despesa adicionada.')
    mes = request.form.get('mes_redirect', '')
    return redirect(url_for('financeiro', mes=mes) if mes else url_for('financeiro'))


@app.route('/financeiro/despesas/<int:id>/deletar', methods=['POST'])
def despesa_deletar(id):
    conn = get_db()
    conn.execute('DELETE FROM despesas WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Despesa removida.')
    mes = request.form.get('mes_redirect', '')
    return redirect(url_for('financeiro', mes=mes) if mes else url_for('financeiro'))


init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(debug=True, host='0.0.0.0', port=port)

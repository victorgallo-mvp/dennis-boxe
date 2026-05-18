const params = new URLSearchParams(window.location.search);
const editId = params.get('id');
let planosData = [];

async function load() {
    try {
        planosData = await apiFetch('/planos');
        const aluno = editId ? await apiFetch(`/alunos/${editId}`) : null;
        render(aluno);
    } catch(e) {
        document.getElementById('content').innerHTML = `<div class="empty">Erro: ${escHtml(e.message)}</div>`;
    }
}

function sel(opts, current) {
    return opts.map(([v,l]) => `<option value="${escHtml(v)}" ${(current||'').trim() === v.trim() ? 'selected' : ''}>${escHtml(l)}</option>`).join('');
}

function render(a) {
    const v = a || {};
    const planosOpts = `<option value="">— Selecione —</option>` +
        planosData.map(p => `<option value="${escHtml(p.nome)}" data-preco="${p.preco}" ${(v.plano_nome||'').trim()===p.nome.trim()?'selected':''}>${escHtml(p.nome)} — R$ ${p.preco|0}</option>`).join('');

    document.getElementById('content').innerHTML = `
    <div class="page-header">
        <h1>${editId ? 'Editar: ' + escHtml(v.nome||'') : 'Novo Aluno'}</h1>
        <a href="/alunos" class="btn btn-ghost">← Voltar</a>
    </div>
    <div class="form-card">
    <form id="form" onsubmit="salvar(event)">
        <div class="form-grid">
            <div class="form-group full">
                <label>Nome completo *</label>
                <input name="nome" required value="${escHtml(v.nome||'')}" placeholder="Nome do aluno">
            </div>
            <div class="form-group">
                <label>Plano</label>
                <select name="plano_nome" id="sel-plano" onchange="preencherValor()">${planosOpts}</select>
            </div>
            <div class="form-group">
                <label>Valor Mensal (R$)</label>
                <input type="number" name="valor_mensal" id="inp-valor" step="0.01" min="0" value="${escHtml(v.valor_mensal||'')}">
                <div class="hint">Preenchido ao selecionar o plano.</div>
            </div>
            <div class="form-group">
                <label>Tipo de Plano</label>
                <select name="tipo_plano" id="sel-tipo" onchange="calcProximo()">
                    ${sel([['Mensal','Mensal'],['Trimestral','Trimestral'],['Semestral','Semestral']], (v.tipo_plano||'Mensal').replace(/\s/g,''))}
                </select>
            </div>
            <div class="form-group">
                <label>Sistema de Pagamento</label>
                <select name="sistema_pagamento">
                    ${sel([['PIX','PIX'],['Dinheiro','Dinheiro'],['Cartão','Cartão'],['Outro','Outro']], v.sistema_pagamento||'PIX')}
                </select>
            </div>
            <div class="form-group">
                <label>Último Pagamento</label>
                <input type="date" name="ultimo_pagamento" id="inp-ultimo" value="${escHtml(v.ultimo_pagamento||'')}" onchange="calcProximo()">
            </div>
            <div class="form-group">
                <label>Próximo Pagamento</label>
                <input type="date" name="proximo_pagamento" id="inp-proximo" value="${escHtml(v.proximo_pagamento||'')}">
                <div class="hint">Calculado automaticamente ou edite manualmente.</div>
            </div>
            <div class="form-group full">
                <label>Horários das Aulas</label>
                <input name="horarios" value="${escHtml(v.horarios||'')}" placeholder="ex: 07:00 (Seg, Qua, Sex)">
            </div>
            <div class="form-group">
                <label>Frequência Média (vezes/semana)</label>
                <input type="number" name="frequencia_semana" step="0.5" min="0" max="7" value="${escHtml(v.frequencia_semana||'')}">
            </div>
            <div class="form-group full">
                <label>Observações</label>
                <textarea name="observacoes">${escHtml(v.observacoes||'')}</textarea>
            </div>
        </div>
        <div class="form-actions">
            <button type="submit" class="btn btn-primary">${editId ? 'Salvar alterações' : 'Adicionar aluno'}</button>
            <a href="/alunos" class="btn btn-secondary">Cancelar</a>
        </div>
    </form>
    </div>`;
}

function preencherValor() {
    const sel = document.getElementById('sel-plano');
    const preco = sel.options[sel.selectedIndex]?.dataset?.preco;
    if (preco) document.getElementById('inp-valor').value = preco;
    calcProximo();
}

function calcProximo() {
    const ultimo = document.getElementById('inp-ultimo').value;
    const tipo   = document.getElementById('sel-tipo').value;
    if (!ultimo) return;
    const dt = new Date(ultimo + 'T00:00:00');
    dt.setMonth(dt.getMonth() + (tipo === 'Semestral' ? 6 : tipo === 'Trimestral' ? 3 : 1));
    document.getElementById('inp-proximo').value =
        `${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,'0')}-${String(dt.getDate()).padStart(2,'0')}`;
}

async function salvar(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    // clean empty strings to null
    Object.keys(body).forEach(k => { if (body[k] === '') body[k] = null; });
    try {
        if (editId) {
            await apiFetch(`/alunos/${editId}`, { method: 'PUT', body: JSON.stringify(body) });
            toast('Aluno atualizado.');
        } else {
            await apiFetch('/alunos', { method: 'POST', body: JSON.stringify(body) });
            toast('Aluno adicionado.');
        }
        setTimeout(() => window.location = '/alunos', 800);
    } catch(e) { toast(e.message, 'error'); }
}

document.addEventListener('DOMContentLoaded', load);

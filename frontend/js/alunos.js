let currentBusca = '', currentStatus = '';

async function load() {
    const params = new URLSearchParams(window.location.search);
    currentBusca  = params.get('busca')  || '';
    currentStatus = params.get('status') || '';
    try {
        const q = new URLSearchParams();
        if (currentBusca)  q.set('busca',  currentBusca);
        if (currentStatus) q.set('status', currentStatus);
        const data = await apiFetch('/alunos?' + q);
        render(Array.isArray(data) ? data : []);
    } catch(e) {
        document.getElementById('content').innerHTML = `<div class="empty">Erro: ${escHtml(e.message)}</div>`;
    }
}

function render(alunos) {
    const filterTabs = [
        { key:'',            label:'Todos' },
        { key:'vencido',     label:'Vencidos' },
        { key:'vence_breve', label:'Vence em breve' },
        { key:'vence_hoje',  label:'Vence hoje' },
        { key:'em_dia',      label:'Em dia' },
        { key:'indefinido',  label:'Indefinido' },
        { key:'pausado',     label:'Pausados' },
    ].map(t => `<a href="?${currentBusca ? 'busca='+encodeURIComponent(currentBusca)+'&' : ''}status=${t.key}" class="ftab ${currentStatus===t.key?'ftab-active':''}">${escHtml(t.label)}</a>`).join('');

    const rows = alunos.map(a => {
        const pausado = a.pausado || a.status === 'pausado';
        const acoes = pausado ? `
            <button class="btn btn-sm btn-secondary" onclick="reativar(${a.id},'${escHtml(a.nome)}')">Reativar</button>
            <a href="/aluno-form?id=${a.id}" class="btn btn-sm btn-ghost">Editar</a>
            <button class="btn btn-sm btn-danger" onclick="deletar(${a.id},'${escHtml(a.nome)}')">✕</button>
        ` : `
            <button class="btn btn-sm btn-secondary" onclick="pagar(${a.id},'${escHtml(a.nome)}')">✓ Pago</button>
            <a href="/aluno-form?id=${a.id}" class="btn btn-sm btn-ghost">Editar</a>
            <button class="btn btn-sm btn-ghost" onclick="toggleHistorico(${a.id}, this)" title="Histórico de pagamentos">Histórico</button>
            <button class="btn btn-sm btn-ghost" onclick="pausar(${a.id},'${escHtml(a.nome)}')" title="Pausar mensalidade">Pausar</button>
            <button class="btn btn-sm btn-danger" onclick="deletar(${a.id},'${escHtml(a.nome)}')">✕</button>
        `;
        return `
        <tr id="row-${a.id}" ${pausado ? 'style="opacity:0.55"' : ''}>
            <td><strong>${escHtml(a.nome)}</strong></td>
            <td>${escHtml(a.plano_nome||'—')}</td>
            <td class="nowrap">${escHtml(a.tipo_plano||'—')}</td>
            <td class="nowrap">${brl(a.valor_mensal)}</td>
            <td>${escHtml(a.sistema_pagamento||'—')}</td>
            <td class="nowrap">${datebr(a.ultimo_pagamento)}</td>
            <td class="nowrap">${datebr(a.proximo_pagamento)}</td>
            <td>${escHtml(a.horarios||'—')}</td>
            <td class="text-right">${a.frequencia_semana ? Math.round(a.frequencia_semana)+'x' : '—'}</td>
            <td>${badge(a.status, a.status_label)}</td>
            <td><div class="actions">${acoes}</div></td>
        </tr>
        ${a.observacoes ? `<tr><td></td><td colspan="10" style="padding-top:2px;padding-bottom:8px"><span class="text-muted" style="font-size:12px">${escHtml(a.observacoes)}</span></td></tr>` : ''}
        <tr id="hist-${a.id}" style="display:none">
            <td colspan="11" style="padding:0">
                <div id="hist-content-${a.id}" style="padding:14px 16px 16px;background:#fafafa;border-bottom:1px solid #e8e8e8"></div>
            </td>
        </tr>`;
    }).join('');

    document.getElementById('content').innerHTML = `
    <div class="page-header">
        <h1>Alunos</h1>
        <a href="/aluno-form" class="btn btn-primary">+ Novo aluno</a>
    </div>
    <div class="toolbar">
        <form onsubmit="buscar(event)">
            <input type="search" id="inp-busca" value="${escHtml(currentBusca)}" placeholder="Buscar por nome…" style="width:220px">
            <button class="btn btn-secondary" type="submit" style="margin-left:8px">Buscar</button>
            ${currentBusca ? `<a href="/alunos" class="btn btn-ghost" style="margin-left:8px">Limpar</a>` : ''}
        </form>
    </div>
    <div class="filter-tabs mb-20">${filterTabs}</div>
    ${alunos.length ? `
    <div class="table-wrap"><table>
        <thead><tr>
            <th>Aluno</th><th>Plano</th><th>Tipo</th><th>Valor</th><th>Pagamento</th>
            <th>Último Pgto</th><th>Próx. Pgto</th><th>Horários</th><th>Freq./sem</th><th>Status</th><th></th>
        </tr></thead>
        <tbody>${rows}</tbody>
    </table></div>` : `<div class="empty">Nenhum aluno encontrado.</div>`}`;
}

async function toggleHistorico(id, btn) {
    const row     = document.getElementById(`hist-${id}`);
    const content = document.getElementById(`hist-content-${id}`);

    if (row.style.display !== 'none') {
        row.style.display = 'none';
        btn.textContent = 'Histórico';
        return;
    }

    row.style.display = '';
    btn.textContent = 'Fechar';
    content.innerHTML = '<div class="empty" style="padding:16px">Carregando…</div>';

    try {
        const pagamentos = await apiFetch(`/alunos/${id}/pagamentos`);
        if (!pagamentos.length) {
            content.innerHTML = '<div class="empty" style="padding:16px">Nenhum pagamento registrado.</div>';
            return;
        }

        const total = pagamentos.reduce((s, p) => s + p.valor, 0);
        content.innerHTML = `
        <div style="font-size:12px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px">
            Histórico de Pagamentos (${pagamentos.length})
        </div>
        <table style="font-size:13px;width:auto;min-width:320px">
            <thead>
                <tr>
                    <th style="padding:6px 12px 6px 0">Data</th>
                    <th style="padding:6px 12px" class="text-right">Valor</th>
                </tr>
            </thead>
            <tbody>
                ${pagamentos.map(p => `
                <tr>
                    <td style="padding:6px 12px 6px 0" class="nowrap">${datebr(p.data)}</td>
                    <td style="padding:6px 12px" class="text-right nowrap">${brl(p.valor)}</td>
                </tr>`).join('')}
            </tbody>
            <tfoot>
                <tr>
                    <td style="padding-top:8px;font-weight:600;font-size:12px;border-top:1px solid #e2e2e2">Total</td>
                    <td style="padding-top:8px;font-weight:700;border-top:1px solid #e2e2e2" class="text-right nowrap">${brl(total)}</td>
                </tr>
            </tfoot>
        </table>`;
    } catch(e) {
        content.innerHTML = `<div class="empty" style="padding:16px">Erro: ${escHtml(e.message)}</div>`;
    }
}

function buscar(e) {
    e.preventDefault();
    const v = document.getElementById('inp-busca').value.trim();
    window.location = '/alunos' + (v ? '?busca=' + encodeURIComponent(v) : '');
}

async function pagar(id, nome) {
    if (!confirm(`Confirmar pagamento de ${nome}?`)) return;
    try {
        const r = await apiFetch(`/alunos/${id}/pagar`, { method: 'POST' });
        toast(r.message); load();
    } catch(e) { toast(e.message, 'error'); }
}

async function pausar(id, nome) {
    if (!confirm(`Pausar mensalidade de ${nome}?\nO aluno não contabilizará no financeiro enquanto pausado.`)) return;
    try {
        await apiFetch(`/alunos/${id}/pausar`, { method: 'POST' });
        toast(`${nome} pausado.`); load();
    } catch(e) { toast(e.message, 'error'); }
}

async function reativar(id, nome) {
    if (!confirm(`Reativar ${nome}?`)) return;
    try {
        await apiFetch(`/alunos/${id}/reativar`, { method: 'POST' });
        toast(`${nome} reativado.`); load();
    } catch(e) { toast(e.message, 'error'); }
}

async function deletar(id, nome) {
    if (!confirm(`Remover ${nome}?`)) return;
    try {
        await apiFetch(`/alunos/${id}`, { method: 'DELETE' });
        toast('Aluno removido.'); load();
    } catch(e) { toast(e.message, 'error'); }
}

document.addEventListener('DOMContentLoaded', load);

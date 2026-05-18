let currentBusca = '', currentStatus = '';

async function load() {
    const params = new URLSearchParams(window.location.search);
    currentBusca  = params.get('busca')  || '';
    currentStatus = params.get('status') || '';
    try {
        const q = new URLSearchParams();
        if (currentBusca)  q.set('busca',  currentBusca);
        if (currentStatus) q.set('status', currentStatus);
        render(await apiFetch('/alunos?' + q));
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
    ].map(t => `<a href="?${currentBusca ? 'busca='+encodeURIComponent(currentBusca)+'&' : ''}status=${t.key}" class="ftab ${currentStatus===t.key?'ftab-active':''}">${escHtml(t.label)}</a>`).join('');

    const rows = alunos.map(a => `
        <tr>
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
            <td>
                <div class="actions">
                    <button class="btn btn-sm btn-secondary" onclick="pagar(${a.id},'${escHtml(a.nome)}')">✓ Pago</button>
                    <a href="/aluno-form?id=${a.id}" class="btn btn-sm btn-ghost">Editar</a>
                    <button class="btn btn-sm btn-danger" onclick="deletar(${a.id},'${escHtml(a.nome)}')">✕</button>
                </div>
            </td>
        </tr>
        ${a.observacoes ? `<tr><td></td><td colspan="10" style="padding-top:2px;padding-bottom:8px"><span class="text-muted" style="font-size:12px">${escHtml(a.observacoes)}</span></td></tr>` : ''}
    `).join('');

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

async function deletar(id, nome) {
    if (!confirm(`Remover ${nome}?`)) return;
    try {
        await apiFetch(`/alunos/${id}`, { method: 'DELETE' });
        toast('Aluno removido.'); load();
    } catch(e) { toast(e.message, 'error'); }
}

document.addEventListener('DOMContentLoaded', load);

async function load() {
    try {
        render(await apiFetch('/dashboard'));
    } catch(e) {
        document.getElementById('content').innerHTML = `<div class="empty">Erro: ${escHtml(e.message)}</div>`;
    }
}

function render(d) {
    const hoje = new Date(d.hoje + 'T12:00:00');
    let h = `
    <div class="page-header">
        <h1>Dashboard</h1>
        <span class="sub">${hoje.toLocaleDateString('pt-BR')}</span>
    </div>`;

    if (d.vencidos.length) {
        const rows = [...d.vencidos]
            .sort((a,b) => (a.proximo_pagamento||'').localeCompare(b.proximo_pagamento||''))
            .map(a => `<tr>
                <td data-label="Aluno"><strong>${escHtml(a.nome)}</strong></td>
                <td data-label="Plano">${escHtml(a.plano_nome||'—')}</td>
                <td data-label="Tipo">${escHtml(a.tipo_plano||'—')}</td>
                <td data-label="Valor" class="nowrap">${brl(a.valor_mensal)}</td>
                <td data-label="Último Pgto" class="nowrap">${datebr(a.ultimo_pagamento)}</td>
                <td data-label="Vencimento">${badge('vencido', datebr(a.proximo_pagamento))}</td>
                <td>
                    <div class="actions">
                        <button class="btn btn-sm btn-secondary" onclick="pagar(${a.id},'${escHtml(a.nome)}')">✓ Confirmar Pagamento</button>
                    </div>
                </td>
            </tr>`).join('');
        h += `
        <div class="section">
            <div class="section-title">Pagamentos Vencidos — ${d.vencidos.length}</div>
            <div class="table-wrap">
            <table class="dash-table">
                <thead><tr><th>Aluno</th><th>Plano</th><th>Tipo</th><th>Valor</th><th>Último Pgto</th><th>Vencimento</th><th></th></tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>`;
    }

    if (d.vence_breve.length) {
        const rows = [...d.vence_breve]
            .sort((a,b) => (a.proximo_pagamento||'').localeCompare(b.proximo_pagamento||''))
            .map(a => `<tr>
                <td data-label="Aluno"><strong>${escHtml(a.nome)}</strong></td>
                <td data-label="Plano">${escHtml(a.plano_nome||'—')}</td>
                <td data-label="Tipo">${escHtml(a.tipo_plano||'—')}</td>
                <td data-label="Valor" class="nowrap">${brl(a.valor_mensal)}</td>
                <td data-label="Vencimento" class="nowrap">${datebr(a.proximo_pagamento)}</td>
                <td data-label="Status">${badge(a.status, a.status_label)}</td>
            </tr>`).join('');
        h += `
        <div class="section">
            <div class="section-title">Vencendo em Breve — ${d.vence_breve.length}</div>
            <div class="table-wrap">
            <table class="dash-table">
                <thead><tr><th>Aluno</th><th>Plano</th><th>Tipo</th><th>Valor</th><th>Vencimento</th><th>Status</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>
            </div>
        </div>`;
    }

    if (!d.vencidos.length && !d.vence_breve.length)
        h += `<div class="empty" style="margin-top:32px">Nenhum pagamento vencido ou próximo do vencimento.</div>`;

    document.getElementById('content').innerHTML = h;
}

async function pagar(id, nome) {
    if (!confirm(`Confirmar pagamento de ${nome}?`)) return;
    try {
        const r = await apiFetch(`/alunos/${id}/pagar`, { method: 'POST' });
        toast(r.message);
        render(await apiFetch('/dashboard'));
    } catch(e) { toast(e.message, 'error'); }
}

document.addEventListener('DOMContentLoaded', load);

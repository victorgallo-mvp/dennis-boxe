async function load() {
    try {
        render(await apiFetch('/dashboard'));
    } catch(e) {
        document.getElementById('content').innerHTML = `<div class="empty">Erro: ${escHtml(e.message)}</div>`;
    }
}

function render(d) {
    const hoje = new Date(d.hoje + 'T12:00:00');
    const mesLabel = hoje.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' });

    let h = `
    <div class="page-header">
        <h1>Dashboard</h1>
        <span class="sub">${hoje.toLocaleDateString('pt-BR')}</span>
    </div>
    <div class="cards">
        <div class="card"><div class="card-label">Alunos Ativos</div><div class="card-value">${d.total_alunos}</div></div>
        <div class="card"><div class="card-label">Receita Mensal Estimada</div><div class="card-value">${brl(d.receita_mensal)}</div></div>
        <div class="card"><div class="card-label">Confirmado — ${mesLabel}</div><div class="card-value">${brl(d.confirmado_mes)}</div></div>
        <div class="card"><div class="card-label">Saldo — ${mesLabel}</div><div class="card-value">${brl(d.saldo)}</div></div>
    </div>`;

    if (d.vencidos.length) {
        const rows = [...d.vencidos].sort((a,b) => (a.proximo_pagamento||'').localeCompare(b.proximo_pagamento||''))
            .map(a => `<tr>
                <td>${escHtml(a.nome)}</td>
                <td>${escHtml(a.plano_nome||'—')}</td>
                <td>${escHtml(a.tipo_plano||'—')}</td>
                <td class="nowrap">${brl(a.valor_mensal)}</td>
                <td class="nowrap">${datebr(a.ultimo_pagamento)}</td>
                <td>${badge('vencido', datebr(a.proximo_pagamento))}</td>
                <td><button class="btn btn-sm btn-secondary" onclick="pagar(${a.id},'${escHtml(a.nome)}')">✓ Confirmar Pagamento</button></td>
            </tr>`).join('');
        h += `<div class="section"><div class="section-title">Pagamentos Vencidos — ${d.vencidos.length}</div>
        <div class="table-wrap"><table>
            <thead><tr><th>Aluno</th><th>Plano</th><th>Tipo</th><th>Valor</th><th>Último Pagamento</th><th>Vencimento</th><th></th></tr></thead>
            <tbody>${rows}</tbody>
        </table></div></div>`;
    }

    if (d.vence_breve.length) {
        const rows = [...d.vence_breve].sort((a,b) => (a.proximo_pagamento||'').localeCompare(b.proximo_pagamento||''))
            .map(a => `<tr>
                <td>${escHtml(a.nome)}</td>
                <td>${escHtml(a.plano_nome||'—')}</td>
                <td>${escHtml(a.tipo_plano||'—')}</td>
                <td class="nowrap">${brl(a.valor_mensal)}</td>
                <td class="nowrap">${datebr(a.proximo_pagamento)}</td>
                <td>${badge(a.status, a.status_label)}</td>
            </tr>`).join('');
        h += `<div class="section"><div class="section-title">Vencendo em Breve — ${d.vence_breve.length}</div>
        <div class="table-wrap"><table>
            <thead><tr><th>Aluno</th><th>Plano</th><th>Tipo</th><th>Valor</th><th>Vencimento</th><th>Status</th></tr></thead>
            <tbody>${rows}</tbody>
        </table></div></div>`;
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

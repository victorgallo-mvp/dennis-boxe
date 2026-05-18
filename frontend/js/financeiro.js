let currentMes = new Date().toISOString().slice(0, 7);

async function load() {
    const params = new URLSearchParams(window.location.search);
    currentMes = params.get('mes') || new Date().toISOString().slice(0, 7);
    try { render(await apiFetch(`/financeiro?mes=${currentMes}`)); }
    catch(e) { document.getElementById('content').innerHTML = `<div class="empty">Erro: ${escHtml(e.message)}</div>`; }
}

function render(d) {
    const hoje_mes = new Date().toISOString().slice(0, 7);

    const resumoRows = d.receita_por_mes.map(r => `
    <tr ${r.atual ? 'style="font-weight:600"' : ''}>
        <td>${escHtml(r.label)}${r.atual ? ' <span class="text-muted" style="font-size:11px;font-weight:400">mês atual</span>' : ''}</td>
        <td class="text-right nowrap">${brl(r.receita)}</td>
        <td class="text-right nowrap">${brl(r.despesas)}</td>
        <td class="text-right nowrap">${brl(r.saldo)}</td>
    </tr>`).join('');

    const pagRows = d.pagamentos_mes.map(p => `
    <tr>
        <td>${escHtml(p.aluno_nome)}</td>
        <td>${escHtml(p.plano_nome||'—')}</td>
        <td>${escHtml(p.tipo_plano||'—')}</td>
        <td class="nowrap">${datebr(p.data)}</td>
        <td class="text-right nowrap">${brl(p.valor)}</td>
    </tr>`).join('');

    const despRows = d.despesas.map(dp => `
    <tr>
        <td class="nowrap">${datebr(dp.data)}</td>
        <td>${escHtml(dp.descricao)}</td>
        <td>${escHtml(dp.categoria||'—')}</td>
        <td class="text-muted">${escHtml(dp.observacoes||'—')}</td>
        <td class="text-right nowrap">${brl(dp.valor)}</td>
        <td><button class="btn btn-sm btn-danger" onclick="deletarDespesa(${dp.id})">✕</button></td>
    </tr>`).join('');

    document.getElementById('content').innerHTML = `
    <div class="page-header">
        <h1>Financeiro</h1>
        <form onsubmit="filtrarMes(event)" style="display:flex;gap:8px;align-items:center">
            <input type="month" id="inp-mes" value="${escHtml(currentMes)}" style="width:155px;padding:6px 10px;border:1px solid #ddd;border-radius:5px;font-size:13.5px;font-family:inherit">
            <button class="btn btn-secondary" type="submit">Filtrar</button>
            ${currentMes !== hoje_mes ? `<a href="/financeiro" class="btn btn-ghost">Mês atual</a>` : ''}
        </form>
    </div>

    <div class="fin-cards">
        <div class="card">
            <div class="card-label">Receita Confirmada</div>
            <div class="card-value">${brl(d.confirmado_mes)}</div>
            <div class="hint mt-4">Pagamentos em ${escHtml(currentMes)}</div>
        </div>
        <div class="card">
            <div class="card-label">Despesas</div>
            <div class="card-value">${brl(d.total_despesas)}</div>
        </div>
        <div class="card">
            <div class="card-label">Saldo</div>
            <div class="card-value">${brl(d.saldo)}</div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Resumo — Últimos 6 Meses</div>
        <div class="table-wrap"><table>
            <thead><tr><th>Mês</th><th class="text-right">Receita Confirmada</th><th class="text-right">Despesas</th><th class="text-right">Saldo</th></tr></thead>
            <tbody>${resumoRows}</tbody>
        </table></div>
    </div>

    <div class="section">
        <div class="section-title">Pagamentos Confirmados em ${escHtml(currentMes)} (${d.pagamentos_mes.length})</div>
        ${d.pagamentos_mes.length ? `
        <div class="table-wrap"><table>
            <thead><tr><th>Aluno</th><th>Plano</th><th>Tipo</th><th>Data</th><th class="text-right">Valor</th></tr></thead>
            <tbody>${pagRows}</tbody>
            <tfoot><tr>
                <td colspan="4" style="padding-top:10px;font-weight:600;font-size:12px">Total</td>
                <td class="text-right nowrap" style="font-weight:700;padding-top:10px;border-top:2px solid #e2e2e2">${brl(d.confirmado_mes)}</td>
            </tr></tfoot>
        </table></div>` : `<div class="empty">Nenhum pagamento confirmado em ${escHtml(currentMes)}.</div>`}
    </div>

    <div class="add-panel">
        <div class="add-panel-title">Adicionar Despesa</div>
        <form onsubmit="adicionarDespesa(event)">
            <div class="form-grid" style="grid-template-columns:2fr 1fr 1fr 1fr;gap:12px;align-items:end">
                <div class="form-group" style="margin-bottom:0"><label>Descrição *</label><input name="descricao" required placeholder="ex: Aluguel"></div>
                <div class="form-group" style="margin-bottom:0"><label>Valor (R$) *</label><input type="number" name="valor" required step="0.01" min="0" placeholder="0"></div>
                <div class="form-group" style="margin-bottom:0"><label>Data *</label><input type="date" name="data" required value="${new Date().toISOString().slice(0,10)}"></div>
                <div class="form-group" style="margin-bottom:0"><label>Categoria</label>
                    <select name="categoria">
                        <option>Aluguel</option><option>Manutenção</option><option>Marketing</option>
                        <option>Material</option><option>Equipamento</option><option>Salário</option><option>Outros</option>
                    </select>
                </div>
            </div>
            <div class="form-group" style="margin-top:10px;margin-bottom:0"><label>Observações</label><input name="observacoes" placeholder="Detalhes adicionais"></div>
            <div style="margin-top:12px"><button type="submit" class="btn btn-primary">Adicionar despesa</button></div>
        </form>
    </div>

    <div class="section">
        <div class="section-title">Despesas em ${escHtml(currentMes)} (${d.despesas.length})</div>
        ${d.despesas.length ? `
        <div class="table-wrap"><table>
            <thead><tr><th>Data</th><th>Descrição</th><th>Categoria</th><th>Observações</th><th class="text-right">Valor</th><th></th></tr></thead>
            <tbody>${despRows}</tbody>
            <tfoot><tr>
                <td colspan="4" style="padding-top:12px;font-weight:600;font-size:13px">Total</td>
                <td class="text-right nowrap" style="font-weight:700;padding-top:12px;border-top:2px solid #e2e2e2">${brl(d.total_despesas)}</td>
                <td></td>
            </tr></tfoot>
        </table></div>` : `<div class="empty">Nenhuma despesa em ${escHtml(currentMes)}.</div>`}
    </div>`;
}

function filtrarMes(e) {
    e.preventDefault();
    const mes = document.getElementById('inp-mes').value;
    window.location = '/financeiro?mes=' + mes;
}

async function adicionarDespesa(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = { descricao: fd.get('descricao'), valor: fd.get('valor'), data: fd.get('data'),
                   categoria: fd.get('categoria'), observacoes: fd.get('observacoes') || null };
    try { await apiFetch('/despesas', { method: 'POST', body: JSON.stringify(body) }); toast('Despesa adicionada.'); load(); }
    catch(e) { toast(e.message, 'error'); }
}

async function deletarDespesa(id) {
    if (!confirm('Remover esta despesa?')) return;
    try { await apiFetch(`/despesas/${id}`, { method: 'DELETE' }); toast('Despesa removida.'); load(); }
    catch(e) { toast(e.message, 'error'); }
}

document.addEventListener('DOMContentLoaded', load);

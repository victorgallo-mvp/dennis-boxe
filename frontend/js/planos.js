async function load() {
    try { render(await apiFetch('/planos')); }
    catch(e) { document.getElementById('content').innerHTML = `<div class="empty">Erro: ${escHtml(e.message)}</div>`; }
}

function render(planos) {
    const rows = planos.map(p => `
    <tr id="row-${p.id}">
        <td><strong>${escHtml(p.nome)}</strong></td>
        <td>${brl(p.preco)}</td>
        <td>${p.valor_aula ? brl(p.valor_aula) : '—'}</td>
        <td>
            <div class="actions">
                <button class="btn btn-sm btn-ghost" onclick="toggleEdit(${p.id})">Editar</button>
                <button class="btn btn-sm btn-danger" onclick="deletar(${p.id},'${escHtml(p.nome)}')">✕</button>
            </div>
            <div id="edit-${p.id}" style="display:none;margin-top:10px;padding:14px;border:1px solid #e2e2e2;border-radius:6px;background:#fff">
                <form onsubmit="salvarEdicao(event,${p.id})">
                    <div class="inline-form">
                        <div class="form-group"><label>Nome</label><input name="nome" value="${escHtml(p.nome)}" required style="width:200px"></div>
                        <div class="form-group"><label>Preço (R$)</label><input type="number" name="preco" value="${p.preco}" required step="0.01" style="width:110px"></div>
                        <div class="form-group"><label>Valor/Aula</label><input type="number" name="valor_aula" value="${p.valor_aula||''}" step="0.01" style="width:110px"></div>
                        <button type="submit" class="btn btn-primary btn-sm" style="align-self:flex-end">Salvar</button>
                        <button type="button" class="btn btn-ghost btn-sm" onclick="toggleEdit(${p.id})" style="align-self:flex-end">Cancelar</button>
                    </div>
                </form>
            </div>
        </td>
    </tr>`).join('');

    document.getElementById('content').innerHTML = `
    <div class="page-header"><h1>Planos</h1></div>
    <div class="add-panel">
        <div class="add-panel-title">Novo Plano</div>
        <form onsubmit="criarPlano(event)">
            <div class="inline-form">
                <div class="form-group"><label>Nome</label><input name="nome" required placeholder="ex: Boxe Coletivo 3x" style="width:220px"></div>
                <div class="form-group"><label>Preço (R$/mês)</label><input type="number" name="preco" required step="0.01" min="0" placeholder="120" style="width:120px"></div>
                <div class="form-group"><label>Valor/Aula (opcional)</label><input type="number" name="valor_aula" step="0.01" placeholder="25" style="width:130px"></div>
                <button type="submit" class="btn btn-primary" style="align-self:flex-end">Adicionar</button>
            </div>
        </form>
    </div>
    ${planos.length ? `
    <div class="table-wrap"><table>
        <thead><tr><th>Plano</th><th>Preço Mensal</th><th>Valor por Aula</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
    </table></div>` : `<div class="empty">Nenhum plano cadastrado.</div>`}`;
}

function toggleEdit(id) {
    const el = document.getElementById(`edit-${id}`);
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function criarPlano(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = { nome: fd.get('nome'), preco: fd.get('preco'), valor_aula: fd.get('valor_aula') || null };
    try { await apiFetch('/planos', { method: 'POST', body: JSON.stringify(body) }); toast('Plano criado.'); load(); }
    catch(e) { toast(e.message, 'error'); }
}

async function salvarEdicao(e, id) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = { nome: fd.get('nome'), preco: fd.get('preco'), valor_aula: fd.get('valor_aula') || null };
    try { await apiFetch(`/planos/${id}`, { method: 'PUT', body: JSON.stringify(body) }); toast('Plano atualizado.'); load(); }
    catch(e) { toast(e.message, 'error'); }
}

async function deletar(id, nome) {
    if (!confirm(`Remover plano "${nome}"?`)) return;
    try { await apiFetch(`/planos/${id}`, { method: 'DELETE' }); toast('Plano removido.'); load(); }
    catch(e) { toast(e.message, 'error'); }
}

document.addEventListener('DOMContentLoaded', load);

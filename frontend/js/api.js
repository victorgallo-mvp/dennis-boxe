const API = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? `http://localhost:${window.location.port || 5050}/api`
    : '/api';

async function apiFetch(path, options = {}) {
    const res = await fetch(API + path, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    const json = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(json.error || `Erro ${res.status}`);
    return json;
}

function brl(v) {
    if (v == null || v === '') return '—';
    return 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function datebr(s) {
    if (!s) return '—';
    const [y, m, d] = s.split('-');
    return `${d}/${m}/${y}`;
}

function escHtml(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function toast(msg, type = 'success') {
    const t = document.createElement('div');
    t.className = `toast${type === 'error' ? ' error' : ''}`;
    t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(() => requestAnimationFrame(() => t.classList.add('show')));
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 3200);
}

function badge(status, label) {
    return `<span class="badge badge-${escHtml(status)}">${escHtml(label)}</span>`;
}

function loading(id = 'content') {
    document.getElementById(id).innerHTML = '<div class="empty">Carregando…</div>';
}

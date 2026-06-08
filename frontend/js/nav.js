document.addEventListener('DOMContentLoaded', () => {
    const p = window.location.pathname.replace(/\.html$/, '');
    const active = (href) => (p === href || (href !== '/' && p.startsWith(href))) ? 'class="active"' : '';
    document.getElementById('nav-placeholder').innerHTML = `
    <nav>
        <a href="/" class="nav-brand">🥊 Dennis Boxe</a>
        <ul>
            <li><a href="/" ${active('/')}>Dashboard</a></li>
            <li><a href="/alunos" ${active('/alunos')}>Alunos</a></li>
            <li><a href="/planos" ${active('/planos')}>Planos</a></li>
            <li><a href="/financeiro" ${active('/financeiro')}>Financeiro</a></li>
        </ul>
    </nav>`;
});

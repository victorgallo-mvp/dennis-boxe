module.exports = async function handler(req, res) {
    let base = (process.env.RAILWAY_URL || '').trim().replace(/\/$/, '');
    if (!base) return res.status(500).json({ error: 'RAILWAY_URL não configurado.' });
    if (!base.startsWith('http')) base = 'https://' + base;

    // req.url em Vercel é apenas '/api/' (mount point).
    // req.query.path contém os segmentos reais: /api/alunos/5/pagar → ['alunos','5','pagar']
    const segments = [].concat(req.query.path || []).filter(Boolean);
    const extra = Object.entries(req.query)
        .filter(([k]) => k !== 'path')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(Array.isArray(v) ? v[0] : v)}`);
    const qs  = extra.length ? '?' + extra.join('&') : '';
    const url = `${base}/api/${segments.join('/')}${qs}`;

    const opts = { method: req.method, headers: { 'Content-Type': 'application/json' } };
    if (req.body && typeof req.body === 'object' && Object.keys(req.body).length > 0) {
        opts.body = JSON.stringify(req.body);
    }

    try {
        const upstream = await fetch(url, opts);
        const text = await upstream.text();
        try {
            return res.status(upstream.status).json(JSON.parse(text));
        } catch {
            const errStatus = upstream.status >= 400 ? upstream.status : 502;
            return res.status(errStatus).json({ error: `Erro ${upstream.status}.`, url, body: text.slice(0, 400) });
        }
    } catch (e) {
        return res.status(502).json({ error: String(e), url });
    }
};

module.exports = async function handler(req, res) {
    let base = (process.env.RAILWAY_URL || '').trim().replace(/\/$/, '');
    if (!base) return res.status(500).json({ error: 'RAILWAY_URL não configurado.' });
    if (!base.startsWith('http')) base = 'https://' + base;

    // Monta URL a partir dos segmentos da catch-all (mais confiável que req.url)
    const segments = [].concat(req.query.path || []);
    const queryParams = new URLSearchParams(
        Object.entries(req.query).filter(([k]) => k !== 'path')
    );
    const qs = queryParams.toString() ? '?' + queryParams.toString() : '';
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
            return res.status(upstream.status).json({ error: `Erro ${upstream.status} no servidor.`, detail: text.slice(0, 300) });
        }
    } catch (e) {
        return res.status(502).json({ error: 'Falha ao conectar: ' + String(e) });
    }
};

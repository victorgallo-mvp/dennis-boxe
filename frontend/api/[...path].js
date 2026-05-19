module.exports = async function handler(req, res) {
    let base = (process.env.RAILWAY_URL || '').trim().replace(/\/$/, '');
    if (!base) return res.status(500).json({ error: 'RAILWAY_URL não configurado.' });
    if (!base.startsWith('http')) base = 'https://' + base;

    // req.url já contém o path completo incluindo /api/ e query string
    const url = base + req.url;

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
            return res.status(errStatus).json({
                error: `Erro ${upstream.status} no servidor.`,
                url,
                body: text.slice(0, 400),
            });
        }
    } catch (e) {
        return res.status(502).json({ error: String(e), url });
    }
};

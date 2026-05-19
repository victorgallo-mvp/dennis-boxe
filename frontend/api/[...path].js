module.exports = async function handler(req, res) {
    let base = (process.env.RAILWAY_URL || '').trim().replace(/\/$/, '');

    if (!base) {
        return res.status(500).json({ error: 'RAILWAY_URL não configurado no Vercel.' });
    }
    if (!base.startsWith('http')) {
        base = 'https://' + base;
    }

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
            // Railway retornou HTML (ex: erro 500) — devolve como JSON legível
            return res.status(upstream.status).json({ error: `Erro ${upstream.status} no servidor.`, detail: text.slice(0, 300) });
        }
    } catch (e) {
        return res.status(502).json({ error: 'Falha ao conectar com o servidor: ' + String(e) });
    }
};

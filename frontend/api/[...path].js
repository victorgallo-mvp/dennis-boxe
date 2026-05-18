module.exports = async function handler(req, res) {
    const base = (process.env.RAILWAY_URL || '').replace(/\/$/, '');

    if (!base) {
        return res.status(500).json({ error: 'RAILWAY_URL não configurado no Vercel.' });
    }

    const url = base + req.url;
    const opts = { method: req.method, headers: { 'Content-Type': 'application/json' } };

    if (req.body && typeof req.body === 'object' && Object.keys(req.body).length > 0) {
        opts.body = JSON.stringify(req.body);
    }

    try {
        const upstream = await fetch(url, opts);
        const data = await upstream.json();
        return res.status(upstream.status).json(data);
    } catch (e) {
        return res.status(502).json({ error: String(e) });
    }
};

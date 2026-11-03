import { kv } from '@vercel/kv';

export default async function handler(req, res) {
  if (req.method === 'GET') {
    const codes = (await kv.get('product_codes')) || {};
    return res.json(codes);
  }

  if (req.method === 'POST') {
    const { product_id, code } = req.body;
    if (!product_id) return res.status(400).json({ error: 'product_id required' });

    const codes = (await kv.get('product_codes')) || {};
    if (code) {
      codes[String(product_id)] = code;
    } else {
      delete codes[String(product_id)];
    }
    await kv.set('product_codes', codes);
    return res.json({ ok: true });
  }

  return res.status(405).json({ error: 'Method not allowed' });
}

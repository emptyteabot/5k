const { buildAnswer, chunkText, setCors } = require('../_engine');

async function readBody(req) {
  if (Buffer.isBuffer(req.body)) {
    const raw = req.body.toString('utf8').trim();
    if (!raw) return {};
    try {
      return JSON.parse(raw);
    } catch {
      return {};
    }
  }
  if (req.body instanceof Uint8Array) {
    const raw = Buffer.from(req.body).toString('utf8').trim();
    if (!raw) return {};
    try {
      return JSON.parse(raw);
    } catch {
      return {};
    }
  }
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body === 'string' && req.body.trim()) {
    try {
      return JSON.parse(req.body);
    } catch {
      return {};
    }
  }
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const raw = Buffer.concat(chunks).toString('utf8').trim();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

module.exports = async function handler(req, res) {
  setCors(req, res);
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  res.writeHead(200, {
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Cache-Control': 'no-cache, no-transform',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no'
  });

  const send = (event, payload) => {
    res.write(`event: ${event}\n`);
    res.write(`data: ${JSON.stringify(payload)}\n\n`);
  };

  try {
    const body = await readBody(req);
    const answer = await buildAnswer(body.message || '', body.clientId || 'public-web');
    send('meta', { title: answer.title || 'BYDFI GPT' });
    for (const part of chunkText(answer.answer || '')) {
      send('delta', { delta: part });
    }
    send('done', answer);
    res.end();
  } catch (error) {
    const fallback = '这次没有连上服务。请再发一次，我会继续接着答。';
    send('meta', { title: 'BYDFI GPT' });
    for (const part of chunkText(fallback)) {
      send('delta', { delta: part });
    }
    send('done', { title: 'BYDFI GPT', answer: fallback, citations: [] });
    res.end();
  }
};

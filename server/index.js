import express from 'express';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PORT = Number(process.env.PORT || 5173);
const isProd = process.env.NODE_ENV === 'production';

const app = express();
app.disable('x-powered-by');

if (isProd) {
  const dist = path.join(root, 'dist');
  app.use(express.static(dist, { index: false, maxAge: '1h', setHeaders(res, file) {
    if (file.endsWith('.html')) res.setHeader('Cache-Control', 'no-cache');
  } }));
  app.get('*', (req, res) => {
    const html = path.join(dist, 'index.html');
    if (!fs.existsSync(html)) return res.status(503).send('Run `npm run build` first.');
    res.sendFile(html);
  });
} else {
  const { createServer } = await import('vite');
  const vite = await createServer({
    root,
    server: { middlewareMode: true, host: '0.0.0.0', allowedHosts: true },
    appType: 'spa',
  });
  app.use(vite.middlewares);
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`JARVIS studio → http://localhost:${PORT} (${isProd ? 'production' : 'dev'})`);
});

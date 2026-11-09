// The mock API over HTTP on 127.0.0.1:<port> (builder F's 8726, DESIGN.md 3): the web app's Vite proxy sends /api to it
// exactly as it would to the real API, so fetches, images and downloads all reach it (Edge makes an <a download> request
// in the browser process, which page.route does not see). The web specs start it in beforeAll when no API server runs
// (WT_SERVE without `api`); the port is checked first and a taken port stops the run with a message. The request's query,
// headers and body bytes reach the mock (the upload milestone's routes: If-Match, withSettings, raw upload parts).
import http from 'node:http';
import net from 'node:net';
import { createMockApi, type MockApi } from './core';

export interface MockServer {
  mock: MockApi;
  url: string;
  close(): Promise<void>;
}

function portIsFree(port: number): Promise<boolean> {
  return new Promise(resolve => {
    const srv = net.createServer();
    srv.once('error', () => resolve(false));
    srv.listen({ port, host: '127.0.0.1', exclusive: true }, () => srv.close(() => resolve(true)));
  });
}

export async function startMockServer(port: number, mock: MockApi = createMockApi()): Promise<MockServer> {
  // A worker restarted after a failed test may find its predecessor's socket closing: give it a few seconds.
  let free = await portIsFree(port);
  for (let i = 0; !free && i < 25; i++) {
    await new Promise(r => setTimeout(r, 200));
    free = await portIsFree(port);
  }
  if (!free) {
    throw new Error(`mock API: port ${port} on 127.0.0.1 is in use; stop whatever holds it or set WT_API_PORT to your own port (DESIGN.md 3)`);
  }
  const server = http.createServer((req, res) => {
    const chunks: Buffer[] = [];
    req.on('data', (c: Buffer) => chunks.push(c));
    req.on('end', () => {
      try {
        const url = new URL(req.url ?? '/', 'http://127.0.0.1');
        const method = (req.method ?? 'GET').toUpperCase();
        const bytes = Buffer.concat(chunks);
        const headers: Record<string, string> = {};
        for (const [k, v] of Object.entries(req.headers)) if (typeof v === 'string') headers[k.toLowerCase()] = v;
        const r = mock.handle({
          method: method === 'HEAD' ? 'GET' : method, path: url.pathname, query: url.search.replace(/^\?/, ''), headers,
          body: bytes.toString('utf8'), bytes,
        });
        res.writeHead(r.status, { ...r.headers, 'content-length': String(r.body.length) });
        res.end(method === 'HEAD' ? undefined : r.body);
      } catch (err) {
        res.writeHead(500, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ error: { code: 'mock_failed', message: String(err) } }));
      }
    });
  });
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve());
  });
  return {
    mock,
    url: `http://127.0.0.1:${port}`,
    close: () => new Promise<void>(resolve => {
      server.closeAllConnections();
      server.close(() => resolve());
    }),
  };
}

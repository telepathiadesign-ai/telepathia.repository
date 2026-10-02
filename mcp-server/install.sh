#!/usr/bin/env bash
# Installs the VPS MCP server as a systemd service on 127.0.0.1:3000.
set -euo pipefail
APP=/opt/vps-mcp
mkdir -p "$APP"
cat > "$APP/package.json" <<'PKG_EOF'
{
  "name": "vps-mcp",
  "version": "1.0.0",
  "description": "Remote MCP server exposing shell and file tools on the VPS",
  "main": "server.mjs",
  "scripts": {
    "start": "node server.mjs"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.31.0",
    "express": "^5.2.1",
    "zod": "^4.6.5"
  },
  "private": true
}
PKG_EOF
cat > "$APP/server.mjs" <<'SERVER_EOF'
import { spawn } from 'node:child_process';
import { timingSafeEqual } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import express from 'express';
import { z } from 'zod';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { hostHeaderValidation } from '@modelcontextprotocol/sdk/server/middleware/hostHeaderValidation.js';

const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || '127.0.0.1';
const TOKEN = process.env.MCP_TOKEN || '';
const ALLOWED_HOSTS = (process.env.ALLOWED_HOSTS || 'mcp.telepathiadesign.com,localhost,127.0.0.1').split(',');
const DEFAULT_CWD = process.env.DEFAULT_CWD || '/root';
const MAX_OUTPUT = 200_000;
const MAX_READ = 1_000_000;

if (TOKEN.length < 32) {
  console.error('MCP_TOKEN must be set and at least 32 characters long');
  process.exit(1);
}

const tokenBuf = Buffer.from(TOKEN);
const tokenMatches = (candidate) => {
  const buf = Buffer.from(candidate || '');
  return buf.length === tokenBuf.length && timingSafeEqual(buf, tokenBuf);
};

const text = (s) => ({ content: [{ type: 'text', text: s }] });
const fail = (s) => ({ content: [{ type: 'text', text: s }], isError: true });

const truncate = (s) =>
  s.length > MAX_OUTPUT ? s.slice(0, MAX_OUTPUT) + `\n…[truncated ${s.length - MAX_OUTPUT} chars]` : s;

function runCommand(command, cwd, timeoutSec) {
  return new Promise((resolve) => {
    const child = spawn('bash', ['-lc', command], { cwd, env: process.env });
    let stdout = '';
    let stderr = '';
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill('SIGKILL');
    }, timeoutSec * 1000);
    child.stdout.on('data', (d) => { if (stdout.length <= MAX_OUTPUT) stdout += d; });
    child.stderr.on('data', (d) => { if (stderr.length <= MAX_OUTPUT) stderr += d; });
    child.on('error', (err) => { clearTimeout(timer); resolve({ code: -1, stdout, stderr: String(err), timedOut }); });
    child.on('close', (code) => { clearTimeout(timer); resolve({ code, stdout, stderr, timedOut }); });
  });
}

function buildServer() {
  const server = new McpServer({ name: 'vps', version: '1.0.0' });

  server.registerTool('run_command', {
    description: 'Run a bash command on the VPS (as the service user) and return exit code, stdout and stderr.',
    inputSchema: {
      command: z.string().describe('Bash command to run'),
      cwd: z.string().optional().describe(`Working directory (default ${DEFAULT_CWD})`),
      timeout_seconds: z.number().int().min(1).max(1800).optional().describe('Kill after this many seconds (default 120)'),
    },
  }, async ({ command, cwd, timeout_seconds }) => {
    console.log(`[run_command] cwd=${cwd || DEFAULT_CWD} ${command}`);
    const r = await runCommand(command, cwd || DEFAULT_CWD, timeout_seconds || 120);
    const out = [
      `exit_code: ${r.code}${r.timedOut ? ' (killed: timeout)' : ''}`,
      r.stdout && `--- stdout ---\n${truncate(r.stdout)}`,
      r.stderr && `--- stderr ---\n${truncate(r.stderr)}`,
    ].filter(Boolean).join('\n');
    return r.code === 0 ? text(out) : fail(out);
  });

  server.registerTool('read_file', {
    description: 'Read a text file on the VPS. Use offset/limit (in lines) for large files.',
    inputSchema: {
      path: z.string().describe('Absolute file path'),
      offset: z.number().int().min(0).optional().describe('First line to return (0-based)'),
      limit: z.number().int().min(1).optional().describe('Number of lines to return'),
    },
  }, async ({ path: p, offset, limit }) => {
    try {
      const stat = await fs.stat(p);
      if (stat.size > MAX_READ && offset === undefined && limit === undefined) {
        return fail(`File is ${stat.size} bytes; pass offset/limit to read part of it.`);
      }
      const lines = (await fs.readFile(p, 'utf8')).split('\n');
      const start = offset || 0;
      const slice = lines.slice(start, limit ? start + limit : undefined);
      return text(truncate(slice.join('\n')));
    } catch (e) {
      return fail(String(e.message || e));
    }
  });

  server.registerTool('write_file', {
    description: 'Create or overwrite a file on the VPS. Parent directories are created as needed.',
    inputSchema: {
      path: z.string().describe('Absolute file path'),
      content: z.string().describe('Full file content'),
    },
  }, async ({ path: p, content }) => {
    console.log(`[write_file] ${p} (${content.length} chars)`);
    try {
      await fs.mkdir(path.dirname(p), { recursive: true });
      await fs.writeFile(p, content);
      return text(`Wrote ${content.length} chars to ${p}`);
    } catch (e) {
      return fail(String(e.message || e));
    }
  });

  server.registerTool('edit_file', {
    description: 'Replace one exact occurrence of old_string with new_string in a file. Fails if old_string is missing or appears more than once.',
    inputSchema: {
      path: z.string().describe('Absolute file path'),
      old_string: z.string().describe('Exact text to replace'),
      new_string: z.string().describe('Replacement text'),
    },
  }, async ({ path: p, old_string, new_string }) => {
    console.log(`[edit_file] ${p}`);
    try {
      const src = await fs.readFile(p, 'utf8');
      const count = src.split(old_string).length - 1;
      if (count !== 1) return fail(`old_string found ${count} times in ${p}; it must appear exactly once.`);
      await fs.writeFile(p, src.replace(old_string, () => new_string));
      return text(`Edited ${p}`);
    } catch (e) {
      return fail(String(e.message || e));
    }
  });

  server.registerTool('list_dir', {
    description: 'List entries in a directory on the VPS.',
    inputSchema: { path: z.string().describe('Absolute directory path') },
  }, async ({ path: p }) => {
    try {
      const entries = await fs.readdir(p, { withFileTypes: true });
      const lines = entries
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((e) => (e.isDirectory() ? `${e.name}/` : e.isSymbolicLink() ? `${e.name}@` : e.name));
      return text(lines.join('\n') || '(empty)');
    } catch (e) {
      return fail(String(e.message || e));
    }
  });

  return server;
}

const app = express();
app.disable('x-powered-by');
app.use(hostHeaderValidation(ALLOWED_HOSTS));

app.use('/:token/mcp', (req, res, next) => {
  if (!tokenMatches(req.params.token)) return res.status(404).end();
  next();
});

app.post('/:token/mcp', express.json({ limit: '20mb' }), async (req, res) => {
  const server = buildServer();
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  res.on('close', () => {
    transport.close();
    server.close();
  });
  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (err) {
    console.error('MCP request failed:', err);
    if (!res.headersSent) {
      res.status(500).json({ jsonrpc: '2.0', error: { code: -32603, message: 'Internal server error' }, id: null });
    }
  }
});

app.all('/:token/mcp', (req, res) => {
  res.status(405).set('Allow', 'POST').json({
    jsonrpc: '2.0', error: { code: -32000, message: 'Method not allowed.' }, id: null,
  });
});

app.use((req, res) => res.status(404).end());

app.listen(PORT, HOST, () => console.log(`MCP server listening on http://${HOST}:${PORT}/<token>/mcp`));
SERVER_EOF
cd "$APP" && npm install --omit=dev --no-audit --no-fund

if [ ! -f /etc/vps-mcp.env ]; then
  umask 077
  echo "MCP_TOKEN=$(openssl rand -hex 32)" > /etc/vps-mcp.env
fi

cat > /etc/systemd/system/vps-mcp.service <<'UNIT_EOF'
[Unit]
Description=VPS MCP server
After=network.target

[Service]
EnvironmentFile=/etc/vps-mcp.env
WorkingDirectory=/opt/vps-mcp
ExecStart=/usr/bin/node /opt/vps-mcp/server.mjs
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
UNIT_EOF

systemctl daemon-reload
systemctl enable --now vps-mcp
systemctl restart vps-mcp
sleep 2

# Remove the temporary nginx site from the certbot attempt
rm -f /etc/nginx/sites-enabled/mcp /etc/nginx/sites-available/mcp
nginx -t >/dev/null 2>&1 && systemctl reload nginx

TOKEN=$(grep MCP_TOKEN /etc/vps-mcp.env | cut -d= -f2)
echo
echo "=== service ==="; systemctl is-active vps-mcp
echo "=== local test (expect 200) ==="
curl -s -o /dev/null -w "%{http_code}\n" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  "http://127.0.0.1:3000/$TOKEN/mcp" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}'
echo "=== cloudflared ==="
systemctl cat cloudflared 2>/dev/null | grep -E '^ExecStart' | sed -E 's/(--token|run) [A-Za-z0-9=_-]{20,}/\1 <redacted>/' || echo "no cloudflared systemd unit"
ls /etc/cloudflared/ ~/.cloudflared/ 2>/dev/null
echo
echo "Connector URL (keep this secret):"
echo "https://mcp.telepathiadesign.com/$TOKEN/mcp"

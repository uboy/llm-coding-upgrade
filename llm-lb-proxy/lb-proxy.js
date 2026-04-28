const http = require("http");

const LISTEN_PORT = 4002;
const MODEL_ALIAS = "qwen36";
const REAL_MODEL = "Qwen_Qwen3.6-35B-A3B-Q3_K_M.gguf";
const BACKENDS_CONFIG = [
  { host: "bm1", port: 8001 },
  { host: "bm2", port: 8001 },
];

const HEALTH_INTERVAL_MS = 15000;
const HEALTH_TIMEOUT_MS  = 5000;
const HEALTH_PATH        = "/health";

// Runtime state per backend
const backends = BACKENDS_CONFIG.map((b) => ({
  ...b,
  healthy: true,
  lastCheck: 0,
  consecutiveFails: 0,
}));

// ── Health checker ──────────────────────────────────────────────────────────

function checkBackend(b) {
  return new Promise((resolve) => {
    const req = http.request(
      { hostname: b.host, port: b.port, path: HEALTH_PATH, method: "GET" },
      (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      }
    );
    req.setTimeout(HEALTH_TIMEOUT_MS, () => { req.destroy(); resolve(false); });
    req.on("error", () => resolve(false));
    req.end();
  });
}

async function runHealthChecks() {
  for (const b of backends) {
    const ok = await checkBackend(b);
    const prev = b.healthy;

    if (ok) {
      b.consecutiveFails = 0;
      b.healthy = true;
    } else {
      b.consecutiveFails++;
      // Mark unhealthy after 2 consecutive failures to avoid flapping
      if (b.consecutiveFails >= 2) b.healthy = false;
    }

    b.lastCheck = Date.now();

    if (prev !== b.healthy) {
      console.log(
        `[health] ${b.host}:${b.port} -> ${b.healthy ? "UP" : "DOWN"} (fails=${b.consecutiveFails})`
      );
    }
  }
}

setInterval(runHealthChecks, HEALTH_INTERVAL_MS);
runHealthChecks();

// ── Round-robin with health filter ─────────────────────────────────────────

let _rrIdx = 0;

function nextBackend(exclude = new Set()) {
  const live = backends.filter((b) => b.healthy && !exclude.has(b));
  const pool = live.length > 0 ? live : backends.filter((b) => !exclude.has(b));

  if (pool.length === 0) {
    return null;
  }

  if (live.length === 0) {
    console.warn("[lb] no healthy untried backends, using remaining backends as fallback");
  }

  const b = pool[_rrIdx % pool.length];
  _rrIdx++;
  return b;
}

function backendLabel(backend) {
  return `${backend.host}:${backend.port}`;
}

function markBackendHealthy(backend) {
  const prev = backend.healthy;
  backend.healthy = true;
  backend.consecutiveFails = 0;
  backend.lastCheck = Date.now();

  if (prev !== backend.healthy) {
    console.log(`[health] ${backendLabel(backend)} -> UP (fails=0)`);
  }
}

function markBackendFailed(backend, reason) {
  const prev = backend.healthy;
  backend.consecutiveFails = Math.max(backend.consecutiveFails + 1, 2);
  backend.healthy = false;
  backend.lastCheck = Date.now();

  if (prev !== backend.healthy) {
    console.log(
      `[health] ${backendLabel(backend)} -> DOWN (fails=${backend.consecutiveFails}, reason=${reason})`
    );
  }
}

// ── Request handlers ────────────────────────────────────────────────────────

function handleModels(res) {
  const alive = backends.filter((b) => b.healthy).map((b) => `${b.host}:${b.port}`);
  const body = JSON.stringify({
    object: "list",
    data: [
      {
        id: MODEL_ALIAS,
        object: "model",
        created: Math.floor(Date.now() / 1000),
        owned_by: "local",
      },
    ],
    _backends: { total: backends.length, healthy: alive.length, up: alive },
  });
  res.writeHead(200, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function handleStatus(res) {
  const info = backends.map((b) => ({
    backend: `${b.host}:${b.port}`,
    healthy: b.healthy,
    consecutiveFails: b.consecutiveFails,
    lastCheckAgoMs: b.lastCheck ? Date.now() - b.lastCheck : null,
  }));
  const body = JSON.stringify({ backends: info }, null, 2);
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(body);
}

const server = http.createServer((clientReq, clientRes) => {
  if (clientReq.method === "OPTIONS") {
    clientRes.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Access-Control-Max-Age": "86400",
    });
    clientRes.end();
    return;
  }

  const url = clientReq.url;

  if (clientReq.method === "GET" && /\/?v1\/models|^\/models/.test(url)) {
    console.log(`[models] GET ${url}`);
    return handleModels(clientRes);
  }

  if (clientReq.method === "GET" && url === "/lb-status") {
    return handleStatus(clientRes);
  }

  const chunks = [];
  clientReq.on("data", (chunk) => chunks.push(chunk));
  clientReq.on("end", () => {
    let rawBody = Buffer.concat(chunks);

    if (rawBody.length > 0) {
      try {
        const json = JSON.parse(rawBody);
        if (json.model === MODEL_ALIAS) {
          json.model = REAL_MODEL;
        }
        rawBody = Buffer.from(JSON.stringify(json));
      } catch {}
    }

    let targetPath = url;
    if (!targetPath.startsWith("/v1")) {
      targetPath = "/v1" + targetPath;
    }

    const attempted = new Set();

    const tryBackend = (backend, attempt) => {
      attempted.add(backend);

      console.log(
        `[lb] ${clientReq.method} ${url} -> ${backendLabel(backend)}${targetPath} (${rawBody.length} bytes, healthy=${backend.healthy}, attempt=${attempt})`
      );

      const proxyReq = http.request(
        {
          hostname: backend.host,
          port: backend.port,
          path: targetPath,
          method: clientReq.method,
          headers: {
            "Content-Type": "application/json",
            "Content-Length": rawBody.length,
          },
        },
        (proxyRes) => {
          markBackendHealthy(backend);

          const headers = { ...proxyRes.headers };
          headers["access-control-allow-origin"] = "*";
          headers["x-lb-backend"] = backendLabel(backend);
          headers["x-lb-attempt"] = String(attempt);
          clientRes.writeHead(proxyRes.statusCode, headers);
          proxyRes.pipe(clientRes);
        }
      );

      proxyReq.on("error", (err) => {
        console.error(
          `[lb error] backend=${backendLabel(backend)} attempt=${attempt} ${err.message}`
        );
        markBackendFailed(backend, err.message);

        const fallback = nextBackend(attempted);
        if (!clientRes.headersSent && fallback) {
          console.warn(
            `[lb retry] request retrying via ${backendLabel(fallback)} after ${backendLabel(backend)} failed`
          );
          return tryBackend(fallback, attempt + 1);
        }

        if (!clientRes.headersSent) {
          clientRes.writeHead(502, { "Content-Type": "application/json" });
        }
        clientRes.end(
          JSON.stringify({ error: { message: `LB proxy error: ${err.message}` } })
        );
      });

      proxyReq.write(rawBody);
      proxyReq.end();
    };

    const backend = nextBackend();
    if (!backend) {
      clientRes.writeHead(503, { "Content-Type": "application/json" });
      clientRes.end(
        JSON.stringify({ error: { message: "LB proxy error: no backend available" } })
      );
      return;
    }

    tryBackend(backend, 1);
  });

  clientReq.on("error", (err) => {
    console.error(`[client error] ${err.message}`);
  });
});

server.listen(LISTEN_PORT, "0.0.0.0", () => {
  console.log(`LLM LB Proxy listening on :${LISTEN_PORT}`);
  console.log(`  Model alias: "${MODEL_ALIAS}" -> "${REAL_MODEL}"`);
  BACKENDS_CONFIG.forEach((b, i) =>
    console.log(`  Backend[${i}]: ${b.host}:${b.port}`)
  );
  console.log(`  Health check: every ${HEALTH_INTERVAL_MS / 1000}s via GET ${HEALTH_PATH}`);
  console.log(`  Status: http://localhost:${LISTEN_PORT}/lb-status`);
});

const http = require("http");

const LISTEN_PORT = 4001;
const TARGET_HOST = "host.docker.internal";
const TARGET_PORT = 8001;
const MODEL_ALIAS = "qwen";
const REAL_MODEL = "Qwen3.5-122B-A10B-Q4_K_M-00001-of-00003.gguf";

function handleModels(res) {
  const body = JSON.stringify({
    object: "list",
    data: [
      {
        id: MODEL_ALIAS,
        object: "model",
        created: Date.now(),
        owned_by: "local",
      },
    ],
  });
  res.writeHead(200, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body),
  });
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
      } catch {
      }
    }

    let targetPath = url;
    if (!targetPath.startsWith("/v1")) {
      targetPath = "/v1" + targetPath;
    }

    console.log(
      `[proxy] ${clientReq.method} ${url} -> ${TARGET_HOST}:${TARGET_PORT}${targetPath} (${rawBody.length} bytes)`
    );

    const proxyReq = http.request(
      {
        hostname: TARGET_HOST,
        port: TARGET_PORT,
        path: targetPath,
        method: clientReq.method,
        headers: {
          "Content-Type": "application/json",
          "Content-Length": rawBody.length,
        },
      },
      (proxyRes) => {
        const headers = { ...proxyRes.headers };
        headers["access-control-allow-origin"] = "*";
        clientRes.writeHead(proxyRes.statusCode, headers);
        proxyRes.pipe(clientRes);
      }
    );

    proxyReq.on("error", (err) => {
      console.error(`[error] ${err.message}`);
      if (!clientRes.headersSent) {
        clientRes.writeHead(502, { "Content-Type": "application/json" });
      }
      clientRes.end(
        JSON.stringify({ error: { message: `Proxy error: ${err.message}` } })
      );
    });

    proxyReq.write(rawBody);
    proxyReq.end();
  });

  clientReq.on("error", (err) => {
    console.error(`[client error] ${err.message}`);
  });
});

server.listen(LISTEN_PORT, "0.0.0.0", () => {
  console.log(`LLM Proxy listening on :${LISTEN_PORT}`);
  console.log(`  -> forwarding to ${TARGET_HOST}:${TARGET_PORT}`);
  console.log(`  Model alias: "${MODEL_ALIAS}" -> "${REAL_MODEL}"`);
  console.log(`  Models endpoint: http://localhost:${LISTEN_PORT}/v1/models`);
  console.log(`  Chat endpoint: http://localhost:${LISTEN_PORT}/v1/chat/completions`);
});

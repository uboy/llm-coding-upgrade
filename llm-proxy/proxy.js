const http = require("http");

const LISTEN_PORT = 4001;
const TARGET_HOST = "host.docker.internal";
const TARGET_PORT = 8001;
const MODEL_ALIAS = "qwen";
const REAL_MODEL = "Qwen3.5-122B-A10B-UD-Q4_K_XL-00001-of-00003.gguf";

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

    let upstreamResponded = false;

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
        upstreamResponded = true;
        // Clear connect timeout — we got headers, upstream is alive
        clearTimeout(connectTimer);

        // Response timeout: 600s (10 min) for long LLM generations
        proxyRes.setTimeout(600000, () => {
          console.error("[timeout] upstream response stalled");
          proxyRes.destroy(new Error("upstream response timeout"));
        });

        const headers = { ...proxyRes.headers };
        headers["access-control-allow-origin"] = "*";
        clientRes.writeHead(proxyRes.statusCode, headers);
        proxyRes.pipe(clientRes);

        // Handle upstream disconnecting mid-stream
        proxyRes.on("error", (err) => {
          console.error(`[upstream error] ${err.message}`);
          if (!clientRes.writableEnded) {
            clientRes.end();
          }
        });
      }
    );

    // Connect timeout: 10s — fail fast if upstream is unreachable
    // Uses socket event to detect actual TCP connect, not inactivity timer
    const connectTimer = setTimeout(() => {
      console.error("[timeout] upstream connect timeout");
      proxyReq.destroy(new Error("connect timeout"));
    }, 10000);

    proxyReq.on("socket", (socket) => {
      if (socket.connecting) {
        socket.once("connect", () => {
          clearTimeout(connectTimer);
        });
      } else {
        // Already connected (keep-alive)
        clearTimeout(connectTimer);
      }
    });

    proxyReq.on("error", (err) => {
      console.error(`[error] ${err.message}`);
      if (!clientRes.headersSent) {
        clientRes.writeHead(502, { "Content-Type": "application/json" });
      }
      clientRes.end(
        JSON.stringify({ error: { message: `Proxy error: ${err.message}` } })
      );
    });

    // If client disconnects prematurely (before upstream responded),
    // abort upstream request to free resources
    // Note: clientReq "close" fires when the readable side finishes, which
    // is normal after reading the request body. We detect real client
    // disconnection via the writable response side closing.
    clientRes.on("close", () => {
      if (!upstreamResponded && !proxyReq.destroyed) {
        proxyReq.destroy();
      }
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

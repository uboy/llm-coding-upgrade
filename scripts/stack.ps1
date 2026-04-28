param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "down", "restart", "status", "logs", "smoke", "render-proxy")]
    [string]$Command,

    [Parameter(Position = 1)]
    [string]$Target = "all"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StackRoot = Split-Path -Parent $ScriptDir
$ConfigFile = if ($env:STACK_CONFIG_FILE) { $env:STACK_CONFIG_FILE } else { Join-Path $StackRoot "stack.env" }

if (-not (Test-Path $ConfigFile)) {
    throw "Missing config file: $ConfigFile"
}

$Config = @{}
foreach ($rawLine in Get-Content -Path $ConfigFile) {
    $line = $rawLine.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) {
        continue
    }
    $parts = $line.Split("=", 2)
    if ($parts.Count -eq 2) {
        $Config[$parts[0]] = $parts[1]
    }
}

function Get-Config([string]$Name) {
    if (-not $Config.ContainsKey($Name)) {
        throw "Missing config value: $Name"
    }
    return $Config[$Name]
}

function Get-ConfigOrFallback([string[]]$Names) {
    foreach ($name in $Names) {
        if ($Config.ContainsKey($name) -and $Config[$name] -ne "") {
            return $Config[$name]
        }
    }
    throw "Missing config value: one of $($Names -join ', ')"
}

function Test-ContainerExists([string]$Name) {
    docker inspect $Name *> $null
    return $LASTEXITCODE -eq 0
}

function Remove-ContainerIfExists([string]$Name) {
    if (Test-ContainerExists $Name) {
        docker rm -f $Name | Out-Null
    }
}

function Render-Proxy {
    $proxyFile = Get-Config "PROXY_FILE"
    $proxyDir = Split-Path -Parent $proxyFile
    if (-not (Test-Path $proxyDir)) {
        New-Item -ItemType Directory -Path $proxyDir -Force | Out-Null
    }

    $listenPort = Get-Config "PROXY_CONTAINER_PORT"
    $targetHost = Get-Config "PROXY_TARGET_HOST"
    $targetPort = Get-Config "PROXY_TARGET_PORT"
    $modelAlias = Get-Config "PROXY_MODEL_ALIAS"
    $realModel = Get-Config "PROXY_REAL_MODEL"

    $content = @"
const http = require("http");

const LISTEN_PORT = $listenPort;
const TARGET_HOST = "$targetHost";
const TARGET_PORT = $targetPort;
const MODEL_ALIAS = "$modelAlias";
const REAL_MODEL = "$realModel";

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

    console.log(`[proxy] ${clientReq.method} ${url} -> ${TARGET_HOST}:${TARGET_PORT}${targetPath} (${rawBody.length} bytes)`);

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
      clientRes.end(JSON.stringify({ error: { message: `Proxy error: ${err.message}` } }));
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
"@

    Set-Content -Path $proxyFile -Value $content -NoNewline
}

function Start-Llama {
    $hostModelPath = Join-Path (Get-Config "LLAMA_MODELS_HOST_DIR") ((Get-Config "LLAMA_MODEL_PATH") -replace '^/models/', '')
    if (-not (Test-Path $hostModelPath)) {
        throw "Missing model file: $hostModelPath"
    }

    docker run -d `
        --name (Get-Config "LLAMA_CONTAINER") `
        --restart unless-stopped `
        --log-opt max-size=100m `
        --log-opt max-file=3 `
        --gpus all `
        -e ("CUDA_VISIBLE_DEVICES=" + (Get-Config "LLAMA_GPU_DEVICES")) `
        -p ((Get-Config "LLAMA_HOST_PORT") + ":" + (Get-Config "LLAMA_CONTAINER_PORT")) `
        -v ((Get-Config "LLAMA_MODELS_HOST_DIR") + ":/models") `
        (Get-Config "LLAMA_IMAGE") `
        -m (Get-Config "LLAMA_MODEL_PATH") `
        --host 0.0.0.0 `
        --port (Get-Config "LLAMA_CONTAINER_PORT") `
        --n-gpu-layers (Get-Config "LLAMA_GPU_LAYERS") `
        --ctx-size (Get-Config "LLAMA_CTX_SIZE") `
        --split-mode (Get-Config "LLAMA_SPLIT_MODE") `
        --tensor-split (Get-Config "LLAMA_TENSOR_SPLIT") `
        --parallel (Get-Config "LLAMA_PARALLEL") `
        --fit (Get-Config "LLAMA_FIT") | Out-Null
}

function Start-Proxy {
    Render-Proxy

    docker run -d `
        --name (Get-Config "PROXY_CONTAINER") `
        --restart unless-stopped `
        -p ((Get-Config "PROXY_HOST_PORT") + ":" + (Get-Config "PROXY_CONTAINER_PORT")) `
        --add-host=host.docker.internal:host-gateway `
        -v ((Get-Config "PROXY_FILE") + ":/app/proxy.js:ro") `
        (Get-Config "PROXY_IMAGE") `
        node /app/proxy.js | Out-Null
}

function Start-OpenWebUI {
    if ((Get-Config "OPENWEBUI_ENABLED") -ne "true") {
        return
    }

    $openAiBaseUrls = Get-ConfigOrFallback @("OPENWEBUI_OPENAI_BASE_URLS", "OPENWEBUI_OPENAI_BASE_URL")
    $openAiApiKeys = Get-ConfigOrFallback @("OPENWEBUI_OPENAI_API_KEYS", "OPENWEBUI_OPENAI_API_KEY")

    docker run -d `
        --name (Get-Config "OPENWEBUI_CONTAINER") `
        --restart unless-stopped `
        --gpus ("device=" + (Get-Config "OPENWEBUI_GPU_DEVICES")) `
        --log-opt max-size=100m `
        --log-opt max-file=3 `
        -v ((Get-Config "OPENWEBUI_DATA_VOLUME") + ":/app/backend/data") `
        -v ((Get-Config "OPENWEBUI_EMBEDDING_HOST_DIR") + ":/app/backend/data/cache/embedding/models/intfloat_multilingual-e5-large:ro") `
        -p ((Get-Config "OPENWEBUI_HOST_PORT") + ":" + (Get-Config "OPENWEBUI_CONTAINER_PORT")) `
        -e ("OPENAI_API_BASE_URLS=" + $openAiBaseUrls) `
        -e ("OPENAI_API_KEYS=" + $openAiApiKeys) `
        -e ("WEBUI_AUTH=" + (Get-Config "OPENWEBUI_WEBUI_AUTH")) `
        -e ("OFFLINE_MODE=" + (Get-Config "OPENWEBUI_OFFLINE_MODE")) `
        -e ("HF_HUB_OFFLINE=" + (Get-Config "OPENWEBUI_HF_HUB_OFFLINE")) `
        -e ("RAG_EMBEDDING_MODEL=" + (Get-Config "OPENWEBUI_RAG_EMBEDDING_MODEL")) `
        -e ("RAG_EMBEDDING_MODEL_AUTO_UPDATE=" + (Get-Config "OPENWEBUI_RAG_EMBEDDING_MODEL_AUTO_UPDATE")) `
        -e ("RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE=" + (Get-Config "OPENWEBUI_RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE")) `
        -e ("WHISPER_MODEL_AUTO_UPDATE=" + (Get-Config "OPENWEBUI_WHISPER_MODEL_AUTO_UPDATE")) `
        -e ("ENABLE_VERSION_UPDATE_CHECK=" + (Get-Config "OPENWEBUI_ENABLE_VERSION_UPDATE_CHECK")) `
        -e ("CUDA_VISIBLE_DEVICES=" + (Get-Config "OPENWEBUI_GPU_DEVICES")) `
        --add-host=host.docker.internal:host-gateway `
        (Get-Config "OPENWEBUI_IMAGE") `
        bash start.sh | Out-Null
}

function Down-Stack {
    Remove-ContainerIfExists (Get-Config "PROXY_CONTAINER")
    Remove-ContainerIfExists (Get-Config "LLAMA_CONTAINER")
    if ((Get-Config "OPENWEBUI_ENABLED") -eq "true") {
        Remove-ContainerIfExists (Get-Config "OPENWEBUI_CONTAINER")
    }
}

function Up-Stack {
    Down-Stack
    Start-Llama
    Start-Proxy
    Start-OpenWebUI
}

function Show-Status {
    $names = @((Get-Config "LLAMA_CONTAINER"), (Get-Config "PROXY_CONTAINER"))
    if ((Get-Config "OPENWEBUI_ENABLED") -eq "true") {
        $names += (Get-Config "OPENWEBUI_CONTAINER")
    }

    docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | Where-Object {
        $line = $_
        if ($names | Where-Object { $line.StartsWith($_ + "`t") }) {
            $true
        } else {
            $false
        }
    }
}

function Show-Logs([string]$LogTarget) {
    switch ($LogTarget) {
        "llama" { docker logs -f (Get-Config "LLAMA_CONTAINER") }
        "proxy" { docker logs -f (Get-Config "PROXY_CONTAINER") }
        "webui" { docker logs -f (Get-Config "OPENWEBUI_CONTAINER") }
        default {
            docker logs --tail 100 (Get-Config "LLAMA_CONTAINER")
            docker logs --tail 100 (Get-Config "PROXY_CONTAINER")
            if ((Get-Config "OPENWEBUI_ENABLED") -eq "true") {
                docker logs --tail 100 (Get-Config "OPENWEBUI_CONTAINER")
            }
        }
    }
}

function Invoke-Smoke {
    $proxyPort = Get-Config "PROXY_HOST_PORT"
    $alias = Get-Config "PROXY_MODEL_ALIAS"
    curl.exe -fsS --max-time 10 ("http://127.0.0.1:" + $proxyPort + "/v1/models")
    Write-Host
    curl.exe -fsS --max-time 120 ("http://127.0.0.1:" + $proxyPort + "/v1/chat/completions") `
        -H "Content-Type: application/json" `
        -d ("{`"model`":`"" + $alias + "`",`"messages`":[{`"role`":`"user`",`"content`":`"Reply with exactly: ok`"}],`"max_tokens`":8,`"stream`":false}")
    Write-Host
}

switch ($Command) {
    "up" { Up-Stack }
    "restart" { Up-Stack }
    "down" { Down-Stack }
    "status" { Show-Status }
    "logs" { Show-Logs $Target }
    "smoke" { Invoke-Smoke }
    "render-proxy" { Render-Proxy }
    default {
        Write-Host "Usage: $(Split-Path -Leaf $MyInvocation.MyCommand.Path) <up|down|restart|status|logs|smoke|render-proxy> [target]"
        exit 1
    }
}

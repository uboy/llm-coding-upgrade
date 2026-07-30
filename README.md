# LLM Coding Upgrade

Self-hosted LLM stack across three servers for coding and general AI workloads.

## Architecture

| Server | IP | Model | Alias | Port | Decode Speed | Context Slot |
|--------|-----|-------|-------|------|-------------|--------------|
| V100 (v100-host) | v100-host | Qwen3.5-122B-A10B UD-Q4_K_XL | `qwen` | 4001/8001 | 42-48 tok/s | 262,144 |
| bm1 | bm1 | Gemma 4 26B-A4B Q4_K_M | `gemma4` | 4002 | ~80 tok/s | 262,144 |
| bm2 | bm2 | Gemma 4 26B-A4B Q4_K_M | `gemma4` | 4002 | ~80 tok/s | 262,144 |

LB proxy (round-robin with health check): `:4002` -> BM1 + BM2

## Key Files

| File | Purpose |
|------|---------|
| `config-card.md` | Production configuration parameters + script reference |
| `decision-log.md` | Accepted decisions + canonical sampling parameters |
| `docs/llm-glossary.md` | Glossary of LLM parameters and architecture |
| `docs/optimization-research.md` | Optimization research findings |
| `docs/quality-evaluation-protocol.md` | Canonical comparison protocol for local and external coding models |
| `stack.env` | V100 stack configuration |
| `lb-proxy.env` | LB proxy configuration |
| `scripts/deploy.sh` | Unified lifecycle manager (V100 + BM + LB) |
| `scripts/apply-model.sh` | Model switching from registry with rollback |
| `scripts/stack.sh` | V100 stack launcher |
| `scripts/lb-stack.sh` | LB proxy launcher |
| `scripts/v100-benchmark.sh` | Benchmark script for speed and quality testing |
| `scripts/run-benchmark.sh` | Universal benchmark runner (prompt quality review) |
| `scripts/run-exec-benchmark.sh` | Executable benchmark runner (generates code, runs real tests, PASS/FAIL) |
| `client-setup.md` | AI client configuration (Cline, Continue, OpenCode, Aider...) |
| `automation.md` | Model-suite automation for comparing candidates |
| `evals/benchmark-suite.json` | Benchmark suite with 10 coding tasks |
| `evals/benchmark-suite-hard.json` | Hard benchmark suite (10 advanced tasks) |
| `evals/exec-benchmark-suite.json` | Executable benchmark suite: 10 real test suites (Python/C++/JS/TS) |
| `evals/quality-task-catalog.json` | Unified catalog of quality-eval tasks, criteria, and comparison targets |

## Current Status

### V100 Server (v100-host)

**Model:** Qwen3.5-122B-A10B UD-Q4_K_XL

| Parameter | Value |
|-----------|-------|
| Proxy alias | `qwen` (port 4001) |
| Proxy URL | `http://v100-host:4001/v1` |
| llama.cpp upstream | `http://127.0.0.1:8001` |
| GPU | 3× Tesla V100 PCIE 32GB (PCIe only, NVLink unavailable) |
| CUDA_VISIBLE_DEVICES | 0,1,2 |

**llama.cpp Parameters:**
```
--n-gpu-layers 100
--ctx-size 262144           # native n_ctx_train
--split-mode layer
--tensor-split 1,1,1
--parallel 1
--batch-size 2048
--ubatch-size 2048
--cache-type-k q4_0
--cache-type-v q4_0
--jinja                     # native chat template for tool-calling
--reasoning on              # thinking-model
--temp 0.6
--top-p 0.95
--top-k 20
--min-p 0.0
--repeat-penalty 1.0        # 1.0 = disabled (thinking models)
```

> `--override-kv` не используется — ctx совпадает с `n_ctx_train=262144`.

**VRAM Usage (2026-05-07, ubatch=2048, parallel=1, ctx=262144, KV Q4_0, UD-Q4_K_XL):**
```
GPU0: 30,180/32,768 MiB (92.1%)
GPU1: 26,350/32,768 MiB (80.4%)
GPU2: 26,424/32,768 MiB (80.6%)
Total: 82,954/98,304 MiB (84.4%)
Weights: ~72 GiB (UD-Q4_K_XL)
```

**Performance (production, 2026-05-07, ubatch=2048, parallel=1, ctx=262144, KV Q4_0):**

| Prompt tokens | PP tok/s | Decode tok/s | Wall time |
|---------------|----------|-------------|-----------|
| 865 | 498.3 | 44.6 | 4.8s |
| 11,785 | 445.0 | 41.6 | 30.2s |
| 75,362 | 369.7 | 23.0 | 183s |
| 150,702 | 246.9 | 22.3 | 320s |

> V100 PP improved by increasing ubatch from 512 to 2048 (D-038).
> Gains: 10K +37%, 64K +42%, 128K +32% over previous config. Decode unchanged.
> Quality suite: 10/10 OK. Artifacts: runs/v100-opt-20260507-181221/

Decode degradation by context:
- 0-2K: **42-48 tok/s**
- 10-65K: **22-28 tok/s**
- 100-256K: **14-25 tok/s**

Cold-start: ~76s

**Architecture Details:**
| Parameter | Value |
|-----------|-------|
| Total params | 122B |
| Active params | 10B |
| Type | MoE (8/64 experts) + SSM |
| Blocks | 48 |
| Attention layers | 12 (interval=4) |
| SSM layers | 36 |
| KV heads (GQA) | 4 |
| Head dim | 128 |
| Embed dim | 2048 |
| n_ctx_train | 262,144 (256K) |
| Thinking | Hybrid |

**Sampling Parameters (canonical, from decision-log.md):**
```
--temp 0.6  --top-p 0.95  --top-k 20  --min-p 0.0
--jinja
```

### bm1

**Model:** Gemma 4 26B-A4B Q4_K_M

| Parameter | Value |
|-----------|-------|
| LB alias | `gemma4` |
| LB URL | `http://v100-host:4002/v1` |
| GPU | 1× RTX 3090 24GB |

**llama.cpp Parameters:**
```
-ngl 100
--ctx-size 262144
--parallel 1
--batch-size 1024 --ubatch-size 256
--cache-type-k q8_0
--cache-type-v q8_0
--reasoning on
--jinja
--temp 0.6
--top-p 0.95
--top-k 20
--min-p 0.0
--override-kv qwen35moe.context_length=int:327680
```

**VRAM Usage (2026-04-24, ctx=327680):**
```
Weights (CUDA0):  15,256 MiB
KV Q8 (328K):       3,400 MiB  ← 10/40 attn layers, rest are SSM
RS buffer:            63 MiB  ← recurrent state (fixed)
Compute buf:         ~350 MiB
─────────────────────────────
Total:  21,195 / 24,576 MiB (86.2%)
```

**Performance (2026-05-18):**
- Decode: **110.9 tok/s**
- Prompt: **300.0 tok/s**
- Quality (10 coding tasks): **8/10 OK** (2 overflow — thinking chain)
- Exec Benchmark (10 real test suites): **6/10 PASS**

### bm2

**Model:** Gemma 4 26B-A4B Q4_K_M

| Parameter | Value |
|-----------|-------|
| LB alias | `gemma4` |
| LB URL | `http://v100-host:4002/v1` |
| GPU | 1× RTX 3090 24GB |

**llama.cpp Parameters:**
```
-ngl 999
--ctx-size 262144
--parallel 1
--batch-size 1024 --ubatch-size 256
--cache-type-k q8_0
--cache-type-v q8_0
--reasoning off
--jinja
--temp 0.6
--top-p 0.95
--top-k 20
--min-p 0.0
--repeat-penalty 1.0
```

**VRAM Usage (2026-05-18, ctx=262144):**
```
Weights (CUDA0):  20,328 / 24,576 MiB (82.7%)
```

**Performance (2026-05-18):**
- Decode: **121.6 tok/s**
- Prompt: **409.3 tok/s**
- Quality (10 standard + 10 hard coding tasks): **20/20 OK**
- Exec Benchmark (10 real test suites): **7/10 PASS**
  - ✅ Python: Template Resolver, JSON Patch, Rate Limiter
  - ✅ C++: LRU Cache, ✅ JavaScript: Async Retry, ✅ TypeScript: Event Bus
  - ✅ Bug-fix: Bank Ledger (3 planted bugs found & fixed)
  - ❌ TTL Cache, ❌ Log Analyzer, ❌ Max Happiness DP

**Architecture Details:**
| Parameter | Value |
|-----------|-------|
| Total params | 26B |
| Active params | 4B |
| Type | MoE |
| Thinking | — (disabled, Fast mode) |
| Vision | ✅ mmproj available |

### Comparison Table (V100 vs BM1 vs BM2)

| Metric | V100 (122B UD-Q4_K_XL) | BM1 (Qwen3.6 35B) | BM2 (Gemma4 26B) |
|--------|------------------------|-------------------|-------------------|
| Decode tok/s | **42-48** | 110.9 | **121.6** |
| Prompt tok/s | 247-445 | 300.0 | **409.3** |
| Quality (10 tasks) | 9/10 | 8/10 (2 overflow) | **10/10** |
| Exec Benchmark (10 real tests) | — | 6/10 | **7/10** |
| Context per slot | 262,144 | 327,680 | 262,144 |
| VRAM usage | 84% | 86% | **83%** |
| Thinking | on | on | off |
| Vision | No | Yes (mmproj) | Yes (mmproj) |

## Management Scripts

### deploy.sh — Unified Lifecycle Manager

Manages all services: V100 stack + LB proxy + BM1/BM2 (via SSH).

```bash
bash scripts/deploy.sh restart            # Restart everything with health-waits
bash scripts/deploy.sh restart-local      # Local services only (V100 + LB)
bash scripts/deploy.sh restart-bm         # BM1/BM2 via SSH only
bash scripts/deploy.sh status             # Status with config params for all services
bash scripts/deploy.sh smoke              # End-to-end smoke on all endpoints
bash scripts/deploy.sh down               # Stop all local services
bash scripts/deploy.sh logs [target]      # Logs: v100, lb, bm1, bm2, all
```

Options: `--env FILE` (alternate stack.env), `--lb-env FILE` (alternate lb-proxy.env)

Restart order with health waits:
1. V100 llama.cpp -> wait `/health` (up to 5 min)
2. BM1/BM2 llama.cpp -> wait `/health` via SSH (up to 5 min)
3. LB proxy -> wait port ready (up to 30s)

### apply-model.sh — Model Switching

Reads `model-suite.models.json`, generates config, restarts, validates, rolls back on failure.

```bash
bash scripts/apply-model.sh list              # List available models
bash scripts/apply-model.sh current           # Show current active config
bash scripts/apply-model.sh apply <model-id>  # Switch model (with rollback)
bash scripts/apply-model.sh apply <id> --no-rollback  # No rollback on failure
```

Full `apply` cycle: parse JSON -> resolve GGUF -> validate -> backup -> generate stack.env -> restart -> wait-ready -> smoke -> rollback on failure.

### stack.sh — V100 Stack

```bash
bash scripts/stack.sh up                      # Start stack
bash scripts/stack.sh down                    # Stop stack
bash scripts/stack.sh restart                 # Restart stack
bash scripts/stack.sh status                  # Container status
bash scripts/stack.sh smoke                   # Smoke test via proxy
bash scripts/stack.sh wait-ready [timeout]    # Wait for llama.cpp /health
bash scripts/stack.sh logs [target]           # Logs: all, llama, proxy, webui
bash scripts/stack.sh render-proxy            # Regenerate proxy.js from config
```

### lb-stack.sh — LB Proxy

```bash
bash scripts/lb-stack.sh up / down / restart / status / smoke / logs
```

## Experiments

| File | Description |
|------|-------------|
| `experiments/model-comparison-full-2026-04-24.md` | Full benchmark V100 vs BM (10 tasks + speed) |
| `experiments/gemma4-vs-qwen36-bm2-2026-05-18.md` | Gemma 4 vs Qwen 3.6 exec test benchmark (10 real test suites, 7/10 vs 6/10) |
| `experiments/quality-eval-results-2026-04-28.md` | Current local quality matrix + placeholders for Codex/Claude |
| `experiments/v100-minimax-m2.7-2026-04-24.md` | MiniMax M2.7 test (not recommended) |
| `experiments/v100-model-comparison-2026-04-23.md` | Comparison of 5 models (wave 1) |
| `experiments/v100-ram-overflow-397b-exp.md` | RAM overflow experiment with Qwen3.5-397B |
| `experiments/upgrade-report-2026-04-22.md` | bm upgrade report |

## Known Limitations

- **V100 long context degradation:** Decode speed drops with context length — 42-48 tok/s at 0-2K, 16-22 tok/s at 10-65K, 14-25 tok/s at 100-256K. Caused by PCIe bottleneck between 3 GPUs (no NVLink). For long prompt processing, redirect to BM (471 tok/s PP).
- **V100 NVLink:** Tesla V100 PCIe supports NVLink 2.0 hardware-wise, but physical bridges are absent.
- **BM thinking overflow:** On complex tasks, the thinking chain consumes the entire token budget, leaving content = 0.
  Mitigation: Use `/no_think` or set max_tokens >= 12000.
- **Flash attention:** Automatically enabled (CC >= 7.0).
- **Speculative decoding:** NOT compatible with hybrid SSM models (Qwen3.5-122B, Qwen3-Coder-Next).
  Error: "the target context does not support partial sequence removal"
  Reason: ssm_d_state in the model — hybrid recurrent layers require full KV-state, speculative decoding cannot roll back rejected tokens.
  Status: Tested 2026-04-13, documented in decision-log.md D-016.

## Quick Start Commands

```bash
# Full status of all services
bash scripts/deploy.sh status

# Restart everything
bash scripts/deploy.sh restart

# Switch V100 model
bash scripts/apply-model.sh list
bash scripts/apply-model.sh apply <model-id>

# Smoke test all endpoints
bash scripts/deploy.sh smoke
```

## Monitoring New Models

- **DeepSeek V4-Flash** (2026-04-24): 158B MoE 6/256, Q4 ~73.6 GiB. GGUF not yet available — wait for unsloth/bartowski (~1 week). The only V4 candidate for V100.

## Benchmarking

### v100-benchmark.sh

Benchmark V100 stack for speed and quality (10 coding tasks).

**Usage:**
```bash
bash scripts/v100-benchmark.sh [--speed-only] [--quality-only] [--task Q01] [--endpoint URL] [--model MODEL]
```

**Options:**
- `--speed-only` — Run only speed benchmark
- `--quality-only` — Run only quality benchmark
- `--task Q01` — Run specific task only
- `--endpoint URL` — Custom endpoint (default: `http://localhost:4001/v1`)
- `--model MODEL` — Custom model (default: `qwen`)

**Environment Variables:**
- `BENCH_ENDPOINT` — Default endpoint
- `BENCH_MODEL` — Default model
- `BENCH_MAX_TOKENS` — Max tokens (default: 7000)
- `BENCH_TIMEOUT` — Request timeout in seconds (default: 300)

**Output:**
Results are saved to `runs/benchmark-YYYYMMDD-HHMMSS/`:
- `speed.json` — Decode + prompt speed metrics
- `quality.json` — Per-task quality results
- `summary.json` — Overall summary
- `<task-id>-response.json` — Full response for each task

**Quality Categories:**
- **OK** — Content > 500 characters
- **PARTIAL** — Content 100-500 characters
- **EMPTY** — Content < 100 characters
- **OVERFLOW** — Thinking chain consumed entire token budget

**Examples:**
```bash
# Full benchmark (speed + quality)
bash scripts/v100-benchmark.sh

# Speed only
bash scripts/v100-benchmark.sh --speed-only

# Quality only, specific task
bash scripts/v100-benchmark.sh --quality-only --task Q01

# Custom endpoint
bash scripts/v100-benchmark.sh --endpoint http://v100-host:4002/v1 --model gemma4
```

## Client Configuration

See `client-setup.md` for detailed setup of AI clients:
- Cline (VSCode)
- Continue (VSCode / JetBrains)
- OpenCode
- Cursor
- Aider
- Claude Code
- Jan
- Open WebUI (pre-configured at `http://v100-host:3000`)

**Endpoints:**
- `qwen`: `http://v100-host:4001/v1` — Qwen3.5-122B (3× V100) — coding
- `gemma4`: `http://v100-host:4002/v1` — Gemma 4 26B-A4B (bm1+2) — general + vision

Both endpoints are OpenAI-compatible. No data leaves the local network.

## Historical Documents (Archive)

- `design.md`, `implementation-plan.md`, `benchmark-plan.md` — completed plans
- `model-comparison-wave1.md` — comparison of 4 models (April 2026)
- `benchmark-results.md` — baseline at 196K / tensor-split 2,2,1 / parallel=1
- `runs/` — model-suite run results
- `artifacts/`, `coordination/` — agent working artifacts

## Stack Configuration

### V100 Stack (stack.env)

Key parameters:
- `LLAMA_MODEL_PATH`: `/models/Qwen3.5-122B-A10B-GGUF/UD-Q4_K_XL/Qwen3.5-122B-A10B-UD-Q4_K_XL-00001-of-00003.gguf`
- `LLAMA_CTX_SIZE`: 262144
- `LLAMA_PARALLEL`: 1
- `LLAMA_BATCH_SIZE`: 2048
- `LLAMA_UBATCH_SIZE`: 2048
- `LLAMA_CACHE_TYPE_K/V`: q4_0
- Sampling: `temp=0.6`, `top-p=0.95`, `top-k=20`, `min-p=0.0`, `repeat-penalty=1.0`

### LB Proxy (lb-proxy.env)

- Round-robin across bm1 (bm1:8001) and bm2 (bm2:8001)
- Health check every 15 seconds
- Auto-retry on ECONNRESET
- `/lb-status` endpoint for monitoring

## Decision Log

All accepted decisions and canonical sampling parameters are documented in `decision-log.md`. Key decisions:

- D-021: V100 prod replacement Qwen3-Coder-Next -> Qwen3.5-122B-A10B Q4_K_M
- D-024: V100: reduce parallel 4->2, increase ctx-size to 589824
- D-025: BM1/2: increase ctx-size 262144->327680
- D-027: override-kv for removing context cap
- D-028: NVLink unavailable on V100 server
- D-029: stack.env updated for Qwen3.5-122B

## Sampling Parameters (Canonical)

Source of truth for sampling parameters. Any disputes should refer to this section first.

### Qwen3.5-122B-A10B (V100, alias `qwen`/`qwen35-122b`, port 4001/8001)
```
--temp 0.6  --top-p 0.95  --top-k 20  --min-p 0.0
--jinja
```
Reasoning: Official Qwen3 thinking model parameters. Generates `<think/>` blocks. DO NOT add `--repeat-penalty`. DO NOT set `--reasoning off`.

### Gemma 4 26B-A4B (bm1/2, alias `gemma4`, port 4002)
```
--temp 0.6  --top-p 0.95  --top-k 20  --min-p 0.0
--repeat-penalty 1.0
--jinja
```
Reasoning: No specific reasoning configuration. Generates `reasoning_content` by default.

## Automation

See `automation.md` for model-suite automation:
- Download GGUF models
- Switch local llama.cpp runtime between candidates
- Direct API benchmark measurements
- OpenCode coding evaluation on fixed test cases
- Hidden-check validation
- Generate final report `summary.json` and `summary.md`

**Key Files:**
- `model-suite.models.json` — candidate list and runtime parameters
- `model-suite.evals.json` — direct benchmarks and formal fixture suite
- `scripts/model_suite.py` — main runner
- `scripts/model-suite.sh` — Linux/macOS wrapper
- `scripts/model-suite.ps1` — Windows wrapper
- `eval-fixtures/` — tracked formal fixtures with auto-tests for Python, C++, JS, and TS
- `runs/` — run results

# LLM Coding Upgrade

Self-hosted LLM stack across three servers for coding and general AI workloads.

## Architecture

| Server | IP | Model | Alias | Port | Decode Speed | Context Slot |
|--------|-----|-------|-------|------|-------------|--------------|
| V100 (v100-host) | v100-host | Qwen3.5-122B-A10B Q4_K_M | `qwen` | 4001/8001 | 42-47 tok/s | 294,912 (×2) |
| bm1 | bm1 | Qwen3.6-35B-A3B Q3_K_M + mmproj | `qwen36` | 4002 | 127.1 tok/s | 327,680 |
| bm2 | bm2 | Qwen3.6-35B-A3B Q3_K_M + mmproj | `qwen36` | 4002 | 127.1 tok/s | 327,680 |

LB proxy (round-robin with health check): `:4002` -> BM1 + BM2

## Key Files

| File | Purpose |
|------|---------|
| `config-card.md` | Production configuration parameters in table format |
| `decision-log.md` | Accepted decisions + canonical sampling parameters |
| `docs/llm-glossary.md` | Glossary of LLM parameters and architecture |
| `docs/optimization-research.md` | Optimization research findings |
| `stack.env` | V100 stack configuration |
| `lb-proxy.env` | LB proxy configuration |
| `scripts/stack.sh` | V100 stack launcher |
| `scripts/lb-stack.sh` | LB proxy launcher |
| `scripts/v100-benchmark.sh` | Benchmark script for speed and quality testing |
| `client-setup.md` | AI client configuration (Cline, Continue, OpenCode, Aider...) |
| `automation.md` | Model-suite automation for comparing candidates |
| `evals/benchmark-suite.json` | Benchmark suite with 10 coding tasks |

## Current Status

### V100 Server (v100-host)

**Model:** Qwen3.5-122B-A10B Q4_K_M

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
--ctx-size 589824           # 2 slots × 294912 tokens
--split-mode layer
--tensor-split 1,1,1
--parallel 2
--cache-type-k q8_0
--cache-type-v q8_0
--jinja                     # native chat template for tool-calling
--reasoning on              # thinking-model
--temp 0.6
--top-p 0.95
--top-k 20
--min-p 0.0
--repeat-penalty 1.0        # 1.0 = disabled (thinking models)
--override-kv qwen35moe.context_length=int:589824  # remove hard cap on n_ctx_train
```

**VRAM Usage (2026-04-24, parallel=2, ctx=589824):**
```
GPU0: 31,412/32,768 MiB (95.8%)  — bottleneck
GPU1: 28,042/32,768 MiB (85.6%)
GPU2: 27,520/32,768 MiB (84.0%)
Total: 86,974/98,304 MiB (88.5%)
KV total: ~7,344 MiB (Q8, ctx=589824, 12 attn layers, 2 slots)
Weights: ~72 GiB (Q4_K_M)
```

**Performance (production, 2026-04-24, parallel=2):**
- Decode: **42-47 tok/s** (ctx=589824, parallel=2, warmed)
- Prompt (short): ~129 tok/s
- Prompt (long, >100K): **~25 tok/s** (PCIe bottleneck between 3 GPUs)
- Cold-start: ~20-100s (depends on warm cache)

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
| n_ctx_train | 262,144 (256K) — overridden to 589,824 via override-kv |
| Thinking | Hybrid |

**Sampling Parameters (canonical, from decision-log.md):**
```
--temp 0.6  --top-p 0.95  --top-k 20  --min-p 0.0
--jinja
```

### bm1 / bm2

**Model:** Qwen3.6-35B-A3B Q3_K_M + mmproj

| Parameter | Value |
|-----------|-------|
| LB alias | `qwen36` |
| LB URL | `http://v100-host:4002/v1` |
| GPU | 1× RTX 3090 24GB (on each server) |

**llama.cpp Parameters:**
```
--n-gpu-layers 100
--ctx-size 327680
--parallel 1
--mmproj mmproj-Qwen_Qwen3.6-35B-A3B-f16.gguf
--batch-size 1024 --ubatch-size 256
--cache-type-k q8_0
--cache-type-v q8_0
--reasoning on
--jinja
--temp 0.6
--top-p 0.95
--top-k 20
--min-p 0.0
--override-kv qwen35moe.context_length=int:327680  # remove hard cap on n_ctx_train
```

**VRAM Usage (2026-04-24, ctx=327680):**
```
Weights (CUDA0):  15,256 MiB
KV Q8 (328K):       3,400 MiB  ← 10/40 attn layers, rest are SSM
RS buffer:            63 MiB  ← recurrent state (fixed)
Compute buf:         ~350 MiB
─────────────────────────────
BM1:  21,195 / 24,576 MiB (86.2%)
BM2:  21,128 / 24,576 MiB (85.9%)
```

**Performance (production, 2026-04-24):**
- Decode: **127.1 tok/s**
- Prompt: **1,501 tok/s**

**Architecture Details:**
| Parameter | Value |
|-----------|-------|
| Total params | 35B |
| Active params | 3B |
| Type | MoE (4/32 experts) + SSM |
| Blocks | 40 |
| Attention layers | 10 (interval=4) |
| SSM layers | 30 |
| KV heads (GQA) | 2 |
| Head dim | 256 |
| Embed dim | 3072 |
| n_ctx_train | 262,144 (256K) — overridden to 327,680 via override-kv |
| Thinking | Hybrid |
| Vision | mmproj |

### Comparison Table (V100 vs BM)

| Metric | V100 (122B Q4) | BM (35B Q3) |
|--------|----------------|-------------|
| Decode tok/s | **23.9** | **127.1** |
| Prompt tok/s | ~128 (est.) | **1,501** |
| Quality | 9/10 | 6/10 |
| Thinking overflow | 1/10 tasks | 4/10 tasks |
| Context per slot | 294,912 | 327,680 |
| Parallel slots | 2 | 1 |
| Vision | No | Yes (mmproj) |

## Experiments

| File | Description |
|------|-------------|
| `experiments/model-comparison-full-2026-04-24.md` | Full benchmark V100 vs BM (10 tasks + speed) |
| `experiments/v100-minimax-m2.7-2026-04-24.md` | MiniMax M2.7 test (not recommended) |
| `experiments/v100-model-comparison-2026-04-23.md` | Comparison of 5 models (wave 1) |
| `experiments/v100-ram-overflow-397b-exp.md` | RAM overflow experiment with Qwen3.5-397B |
| `experiments/upgrade-report-2026-04-22.md` | bm upgrade report |

## Known Limitations

- **V100 prompt processing:** Long prompts (>100K) are processed at ~25 tok/s. A 265K prompt takes ~3 hours.
  Mitigation: Redirect long prompts to BM (1501 tok/s).
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
# Stack status
bash scripts/stack.sh status
bash scripts/lb-stack.sh status
curl http://localhost:4002/lb-status

# Restart V100 stack
bash scripts/stack.sh restart
bash scripts/stack.sh smoke

# Restart LB proxy
bash scripts/lb-stack.sh restart

# Check endpoints
curl http://v100-host:4001/v1/models
curl http://v100-host:4002/v1/models
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
bash scripts/v100-benchmark.sh --endpoint http://v100-host:4002/v1 --model qwen36
```

## Operational Commands

```bash
# V100 stack
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/stack.sh restart
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/stack.sh status
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/stack.sh smoke

# LB proxy
bash /data/home/<user>/proj/llm-coding-upgrade/scripts/lb-stack.sh restart
curl http://localhost:4002/lb-status

# Check endpoints
curl http://v100-host:4001/v1/models
curl http://v100-host:4002/v1/models
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
- `qwen36`: `http://v100-host:4002/v1` — Qwen3.6-35B (bm1+2) — general + vision

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
- `LLAMA_MODEL_PATH`: `/models/Qwen3.5-122B-A10B-GGUF/Q4_K_M/Qwen3.5-122B-A10B-Q4_K_M-00001-of-00003.gguf`
- `LLAMA_CTX_SIZE`: 589824
- `LLAMA_PARALLEL`: 2
- `LLAMA_BATCH_SIZE`: 2048
- `LLAMA_UBATCH_SIZE`: 2048
- `LLAMA_OVERRIDE_KV`: `qwen35moe.context_length=int:589824`
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

### Qwen3.6-35B-A3B (bm1/2, alias `qwen36`, port 4002)
```
--temp 0.6  --top-p 0.95  --top-k 20  --min-p 0.0
--reasoning on
--jinja
```
Reasoning: Official Qwen3 thinking model parameters. Generates `reasoning_content`. DO NOT add `--repeat-penalty`.

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
- `model-suite.evals.json` — direct benchmarks and eval suite
- `scripts/model_suite.py` — main runner
- `scripts/model-suite.sh` — Linux/macOS wrapper
- `scripts/model-suite.ps1` — Windows wrapper
- `eval-fixtures/` — clean test cases
- `runs/` — run results

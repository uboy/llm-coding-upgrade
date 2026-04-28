# References

Источники, использованные при принятии решений. Развёрнутые обоснования — в `decision-log.md`.

## Модели

- **Qwen3-Coder-Next** — https://huggingface.co/Qwen/Qwen3-Coder-Next
  80B total / 3B active, 262K ctx, non-thinking, temp=1.0 top-k=40
- **Qwen3.5-27B** — https://huggingface.co/Qwen/Qwen3.5-27B
  thinking-модель, temp=0.6 top-k=20
- **Qwen3.5-122B-A10B** — https://huggingface.co/Qwen/Qwen3.5-122B
  122B total / 10B active, MoE 8/64, hybrid SSM, thinking model
- **Unsloth GGUF** — https://huggingface.co/unsloth/Qwen3-Coder-Next-GGUF
  Размеры квантизаций, best practices для llama.cpp

## Квантизация

- Unified quantization evaluation (2025) — https://arxiv.org/abs/2601.14277
  Q5_K_S vs Q5_K_M: разница <0.04 ppl, неощутима на 80B → D-015
- llama.cpp quant discussion — https://github.com/ggml-org/llama.cpp/discussions/2094
- KV cache quantization benchmarks — https://github.com/ggml-org/llama.cpp/discussions/5932
  Q8 near-lossless; Q4 даёт -37% decode speed на 110K ctx → оставить Q8

## Sampling параметры

- Vendor-recommended quick reference — https://muxup.com/2025q2/recommended-llm-parameter-quick-reference
- Ivan Fioravanti on Qwen3 thinking params — https://x.com/ivanfioravanti/status/1916934241281061156

## Speculative Decoding

- llama.cpp spec decoding discussion — https://github.com/ggml-org/llama.cpp/discussions/10466
  0.6B draft: 2.5x на coding; 1.5B draft: 1.63x → 0.6B выигрывает → D-016
- llama.cpp spec decoding docs — https://mintlify.wiki/ggml-org/llama.cpp/inference/speculative-decoding
- jukofyork Qwen3-Coder DRAFT 0.75B — https://huggingface.co/jukofyork/Qwen3-Coder-Instruct-DRAFT-0.75B-GGUF
  Для Qwen3-Coder-480B (не Next), как референс построения draft

## Flash Attention на V100

- llama.cpp issue #13008 — https://github.com/ggml-org/llama.cpp/issues/13008
  Подтверждено: llama.cpp fa работает на CC 7.0 (Volta/V100)

## Multi-GPU

- Multi-GPU LLM setup 2026 — https://www.compute-market.com/blog/multi-gpu-local-llm-setup-guide-2026
  Dual RTX 3090: ~15-21 tok/s на 70B Q4; актуально если BM будет иметь 2 GPU

## Обзор рынка coding-моделей (апрель 2026) → D-017

- Qwen3-Coder-Next technical report — https://arxiv.org/html/2603.00729v1
- Qwen3-Coder-Next blog — https://qwen.ai/blog?id=qwen3-coder-next
- Best open-source coding model 2026 (GLM-5 / MiniMax / Kimi / Qwen3) — https://www.morphllm.com/best-open-source-coding-model-2026
- Best AI coding models SWE-bench leaderboard — https://localaimaster.com/models/best-ai-coding-models
- Kimi K2.5 vs Qwen3-Coder-Next — https://www.openaitoolshub.org/en/blog/kimi-k2-5-vs-qwen3-coder-next
- MiniMax M2.5 официальный анонс — https://www.minimax.io/news/minimax-m25
  229B MoE, 10B active (8/256 экспертов), 80.2% SWE-bench; мин. ~126 GB VRAM при NVFP4
- MiniMax M2.5 VRAM и specs — https://apxml.com/models/minimax-m2
- MiniMax M2.5 Unsloth guide — https://unsloth.ai/docs/models/minimax-m25
- Kimi K2.5 VRAM requirements — https://apxml.com/models/kimi-k25
  1T total, 32B active, 76.8% SWE-bench; prod: 2×H100 или 8×A100
- Kimi K2.5 Unsloth guide — https://unsloth.ai/docs/models/kimi-k2.5

## Оптимизация V100 (Хабр статья)

- Статья «Выжать больше из локальных LLM» — https://habr.com/ru/articles/1025132/
  UD-Q4_K_XL лучше Q4_K_M, ncmoe для MoE, -ub/-b для PP speed, ik_llama.cpp
- ik_llama.cpp (форк с IQK квантами) — https://github.com/ikawrakow/ik_llama.cpp
- UD-кванты для ik_llama (ubergarm) — https://huggingface.co/ubergarm
- Unsloth GGUF benchmarks для Qwen3.5 — https://unsloth.ai/docs/models/qwen3.5/gguf-benchmarks

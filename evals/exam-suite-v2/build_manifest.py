#!/usr/bin/env python3
"""Собирает suite.json из каталогов задач + knowledge/questions.json.

Каждая задача: evals/exam-suite-v2/tasks/<id>/. Идентификатор <lang>-<class>-NN:
lang: py|js|cpp|java; класс: algo|api|state|bug|ref|lang (+легаси py-apicontract-kvlite).
Мета-информация берётся из task.json в каталоге задачи (опционально) или выводится из имени.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS = ROOT / "tasks"

CLASS_MAP = {
    "algo": ("algo-ds", None),
    "api": ("api-contract", None),
    "state": ("stateful", None),
    "bug": ("bugfix", None),
    "ref": ("refactor", None),
    "lang": ("lang-specific", None),
}
LANG_MAP = {"py": "python", "js": "javascript", "cpp": "cpp", "java": "java"}

# Без bash: cygwin-шный bash первым в PATH сессии не видит node/javac (грабля 2026-08-28).
# C++/Java гоняются через python-оркестратор runners.py с маркером OK (cygwin abort даёт exit 0).
BROKEN_NAME = {
    "python": "solution.py",
    "javascript": "solution.mjs",
    "cpp": "solution.cpp",
    "java": "Task.java",
}

TEST_CMD = {
    "python": ["python", "-m", "pytest", "tasks/{id}/tests/", "-q", "--no-header"],
    "javascript": ["node", "--test", "tasks/{id}/tests/test_a.mjs"],
    "cpp": ["python", "runners.py", "cpp", "{id}"],
    "java": ["python", "runners.py", "java", "{id}"],
}
TARGET = {
    "python": "tasks/{id}/solution.py",
    "javascript": "tasks/{id}/solution.mjs",
    "cpp": "tasks/{id}/solution.cpp",
    "java": "tasks/{id}/Task.java",
}
PROMPT = {
    "python": "tasks/{id}/README.md",
    "javascript": "tasks/{id}/README.md",
    "cpp": "tasks/{id}/README.md",
    "java": "tasks/{id}/README.md",
}

def main() -> int:
    tasks = []
    for d in sorted(TASKS.iterdir()):
        if not d.is_dir():
            continue
        override = {}
        oj = d / "task.json"
        if oj.exists():
            override = json.loads(oj.read_text(encoding="utf-8"))
        tid = d.name
        if tid == "py-apicontract-kvlite":
            lang, klass, diff = "python", "api-contract", "medium"
        else:
            m = re.match(r"^(py|js|cpp|java)-(algo|api|state|bug|ref|lang)-\d+$", tid)
            if not m:
                print(f"[skip] {tid}: не распознан", file=sys.stderr)
                continue
            lang = LANG_MAP[m.group(1)]
            klass = CLASS_MAP[m.group(2)][0]
            diff = "medium"
        attach = []
        if lang == "cpp":
            attach.append(f"tasks/{tid}/solution.h")
        if klass in ("bugfix", "refactor"):
            attach.append(f"tasks/{tid}/broken/{BROKEN_NAME[lang]}")
        entry = {
            "id": tid,
            "kind": "executable",
            "language": lang,
            "class": klass,
            "difficulty": override.get("difficulty", diff),
            "created": override.get("created", "2026-08-28"),
            "prompt_file": override.get("prompt_file", PROMPT[lang].format(id=tid)),
            "attach": override.get("attach", attach),
            "target_file": override.get("target_file", TARGET[lang].format(id=tid)),
            "test_cmd": [c.format(id=tid) for c in TEST_CMD[lang]],
            "contamination_check": override.get(
                "contamination_check",
                "спецификация авторская (вымышленный домен), дата создания 2026-08-28; "
                "штатная веб-проверка на совпадение с публичными датасетами - фаза 3"),
        }
        tasks.append(entry)

    kn = json.loads((ROOT / "knowledge" / "questions.json").read_text(encoding="utf-8"))
    for item in kn["items"]:
        tasks.append({
            "id": item["id"],
            "kind": "knowledge",
            "language": "text",
            "class": "longtail-knowledge",
            "difficulty": item["difficulty"],
            "created": "2026-08-28",
            "question": item["question"],
            "accepted_answers": item["accepted_answers"],
            **({"answer_extra_required": item["answer_extra_required"]}
               if item.get("answer_extra_required") else {}),
            **({"reject_if": item["reject_if"]}
               if item.get("reject_if") else {}),
            "answer_note": item["answer_note"],
            "contamination_check": item.get("answer_note", "")[:80],
        })

    suite = {
        "suite": "exam-suite-v2",
        "version": "1.0.0",
        "created": "2026-08-28",
        "notes": ("Полный сьют: исполняемые задачи на 4 языках (алгоритмы, контракты API, "
                  "состояние, bugfix, рефакторинг, специфика языка) + вопросы на редкие знания. "
                  "Анти-контаминация: спецификации авторские от 2026-08-28, вымышленные домены; "
                  "знания - стабильные факты из RFC/стандартов с источником в answer_note. "
                  "Скоринг knowledge: вхождение обязательных элементов, лишние не штрафуются."),
        "tasks": tasks,
    }
    out = ROOT / "suite.json"
    out.write_text(json.dumps(suite, indent=2, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    by = Counter((t["language"], t["class"]) for t in tasks)
    print(f"tasks: {len(tasks)} -> {out}")
    for (lang, klass), n in sorted(by.items()):
        print(f"  {lang:10s} {klass:18s} {n}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

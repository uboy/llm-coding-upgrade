#!/usr/bin/env python3
"""Оркестратор тестов для C++/Java (без bash: прямой subprocess, см. граблю с cygwin-bash).

python runners.py cpp <task-id>
python runners.py java <task-id>

Критерий успеха: тестовый бинарник завершился с кодом 0 И напечатал строку OK
(на cygwin abort может давать exit 0, поэтому маркер обязателен).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def ok(output: str) -> bool:
    return any(line.strip() == "OK" for line in output.splitlines())


def run_cpp(task_id: str) -> int:
    d = ROOT / "tasks" / task_id
    exe = d / "_bin"
    compile_cmd = ["g++", "-std=c++17", f"-I{d.as_posix()}", "-o", exe.as_posix(),
                   (d / "solution.cpp").as_posix(), (d / "tests" / "test_main.cpp").as_posix()]
    proc = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=120,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(proc.stderr[:500])
        return 1
    try:
        run = subprocess.run([exe.as_posix()], capture_output=True, text=True, timeout=60,
                             encoding="utf-8", errors="replace")
        passed = run.returncode == 0 and ok(run.stdout + run.stderr)
        print(run.stdout.strip()[-200:])
        return 0 if passed else 1
    finally:
        exe.unlink(missing_ok=True)
        exe.with_suffix(".exe").unlink(missing_ok=True)


def run_java(task_id: str) -> int:
    d = ROOT / "tasks" / task_id
    comp = subprocess.run(["javac", "-d", ".", "Task.java", "TestMain.java"],
                          cwd=str(d), capture_output=True, text=True, timeout=120,
                          encoding="utf-8", errors="replace")
    if comp.returncode != 0:
        print(comp.stderr[:500])
        return 1
    try:
        run = subprocess.run(["java", "TestMain"], cwd=str(d), capture_output=True,
                             text=True, timeout=60, encoding="utf-8", errors="replace")
        passed = run.returncode == 0 and ok(run.stdout + run.stderr)
        print(run.stdout.strip()[-200:])
        return 0 if passed else 1
    finally:
        for cls in d.glob("*.class"):
            cls.unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("cpp", "java"):
        print("usage: runners.py {cpp|java} <task-id>", file=sys.stderr)
        sys.exit(2)
    sys.exit(run_cpp(sys.argv[2]) if sys.argv[1] == "cpp" else run_java(sys.argv[2]))

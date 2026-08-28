#!/usr/bin/env python3
"""Валидатор сьюта: каждая executable-задача обязана иметь зелёный эталон;
bugfix-задачи - красный broken. Java можно пропустить: --skip-java (нет javac локально)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_cmd(cmd: list[str]) -> bool:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                          timeout=180, encoding="utf-8", errors="replace")
    return proc.returncode == 0


def validate(task: dict, variant: str, source: Path | None) -> tuple[bool, str]:
    target = ROOT / task["target_file"]
    existed = target.exists()
    backup = target.with_suffix(target.suffix + ".bak")
    if existed:
        shutil.move(str(target), str(backup))
    try:
        if source is not None:
            shutil.copyfile(str(source), str(target))
        elif not existed:
            return False, "нет ни эталона, ни файла"
        ok = run_cmd(task["test_cmd"])
        return ok, "pass" if ok else "FAIL"
    finally:
        if source is not None:
            target.unlink(missing_ok=True)
        if existed:
            shutil.move(str(backup), str(target))


def reference_path(task: dict) -> Path:
    return ROOT / "tasks" / task["id"] / "reference" / Path(task["target_file"]).name


def broken_path(task: dict) -> Path:
    return ROOT / "tasks" / task["id"] / "broken" / Path(task["target_file"]).name


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-java", action="store_true")
    ap.add_argument("--suite", default=str(ROOT / "suite.json"))
    args = ap.parse_args()

    suite = json.loads(Path(args.suite).read_text(encoding="utf-8"))
    bad = 0
    total = 0
    for t in suite["tasks"]:
        if t["kind"] != "executable":
            continue
        if args.skip_java and t["language"] == "java":
            print(f"[SKIP] {t['id']} (java локально недоступен)")
            continue
        total += 1
        ref_ok, _ = validate(t, "reference", reference_path(t))
        status = "OK" if ref_ok else "REF_FAIL"
        extra = ""
        bp = broken_path(t)
        if bp.exists():
            brok_ok, _ = validate(t, "broken", bp)
            # bugfix: broken обязан падать; refactor: broken обязан проходить (это рабочий код)
            expect_fail = t["class"] == "bugfix"
            brok_good = (not brok_ok) if expect_fail else brok_ok
            status += f" broken={'ok' if brok_good else 'BAD'}"
            if not brok_good:
                status = status.replace("broken=BAD", "broken=BAD(ожидание нарушено)")
                ref_ok = False
        if not ref_ok:
            bad += 1
        print(f"[{status if not ref_ok else 'OK'}] {t['id']}")
    print(f"\nитого: {total} задач, ошибок: {bad}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())

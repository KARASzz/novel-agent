"""Helper to invoke scripts.cli production-run with a hard wall-clock timeout
on macOS, where `timeout` is not on PATH.

Usage:
    python3 scripts/_run_production.py <chapter_count> [from_chapter]
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)


def main() -> int:
    chapter_count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    from_chapter = int(sys.argv[2]) if len(sys.argv) > 2 else None
    model_slot = sys.argv[3] if len(sys.argv) > 3 else "model_slot_3"

    # 35 minutes per chapter should be more than enough.
    per_chapter_seconds = 35 * 60
    wall_clock = per_chapter_seconds * max(chapter_count, 1) + 300  # 5 min overhead
    started = time.time()

    cmd = [
        "python3",
        "-m",
        "scripts.cli",
        "production-run",
        "--project",
        "sample_zerg_queen",
        "--chapters",
        str(chapter_count),
        "--model-slot",
        model_slot,
        "--force",
    ]
    if from_chapter is not None:
        cmd[cmd.index("--chapters") + 1] = str(chapter_count)
        cmd.extend(["--from-chapter", str(from_chapter)])

    print(f"[run] cmd: {' '.join(cmd)}")
    print(f"[run] wall-clock budget: {wall_clock}s")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    last_heartbeat = time.time()
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        if time.time() - last_heartbeat > 60:
            print(f"[heartbeat] elapsed={int(time.time()-started)}s", flush=True)
            last_heartbeat = time.time()
        if time.time() - started > wall_clock:
            print(f"[timeout] killing after {wall_clock}s", flush=True)
            proc.kill()
            break
    proc.wait()
    print(f"[done] exit_code={proc.returncode} elapsed={int(time.time()-started)}s")
    return proc.returncode or 0


if __name__ == "__main__":
    raise SystemExit(main())

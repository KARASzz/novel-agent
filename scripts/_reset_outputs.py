"""一次性脚本：清空 novel_outputs 下所有测试痕迹并重置 progress.json"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOTS = [
    "novel_outputs/console_demo",
    "novel_outputs/packages",
    "novel_outputs/prj_22ec1b0b13_1778774362",
    "novel_outputs/prj_9bfd16201f_1778774006",
    "novel_outputs/prj_ce8565edee_1778773948",
    "novel_outputs/prj_dc4a4fbe42_1778773355",
]

DEFAULT_PROGRESS = {
    "last_completed_chapter_index": 0,
    "next_chapter_index": 1,
    "current_volume": 1,
    "current_arc": 1,
    "current_unit": 1,
    "previous_chapter_writeback": "新书开局，败局重启，无上一章回写。",
    "last_run_id": "",
    "last_review_stop_point": "",
    "state": "ready",
}


def main() -> None:
    for r in ROOTS:
        p = Path(r)
        if p.exists():
            shutil.rmtree(p)
            print(f"rm -rf {r}")

    progress_path = Path("novel_outputs/production_runs/sample_zerg_queen/progress.json")
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(
        json.dumps(DEFAULT_PROGRESS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"reset {progress_path}")

    # 清空生产 runs 目录（已空，再扫一遍保险）
    runs_dir = Path("novel_outputs/production_runs/sample_zerg_queen/runs")
    if runs_dir.exists():
        for child in list(runs_dir.iterdir()):
            if child.is_dir():
                shutil.rmtree(child)
                print(f"rm -rf {child}")

    # 删 .DS_Store 干扰
    ds = Path("novel_outputs/.DS_Store")
    if ds.exists():
        ds.unlink()
        print(f"rm {ds}")


if __name__ == "__main__":
    main()

# 长篇连载生产控制器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建正式长篇连载生产线：每章完整执行九步母版，外层按开篇 1-3 章、4-6 章、后续 `6 / 6 / 6 / 7` 单元停点暂停审稿，并让 CLI 与网页控制台共享同一个生产控制器。

**Architecture:** 新增 `core_engine.production_runner` 作为共享核心，负责项目预设、进度、停点计划、章节串行执行、审稿包与运行摘要。CLI 与网页 API 只调用该核心，不复制生产逻辑。现有 `ChapterOrchestrator` 继续负责单章九步流程，`ProjectPackager` 增加按指定章节根目录打包的能力，避免混入历史 demo 产物。

**Tech Stack:** Python 3.11, FastAPI, Jinja2, pytest, existing `ChapterOrchestrator`, existing `LLMClient`, local JSON/Markdown artifacts.

---

## File Structure

- Modify `config.yaml`: 把 `model_slot_1` 和 `llm.model` 从 MiniMax-M2.7 改为 MiniMax-M3。
- Modify `core_engine/config_loader.py`: 同步默认配置，保证无 `config.yaml` 时也解析到 MiniMax-M3。
- Modify `README.md`: 更新 MiniMax-M3 映射和生产线入口说明。
- Create `core_engine/production_runner.py`: 新的共享生产核心，包含项目预设、进度模型、停点策略、dry-run 计划、真实运行、审稿包生成。
- Modify `core_engine/packager.py`: 增加按指定章节根目录和输出目录打包的方法，保留旧入口兼容。
- Modify `scripts/cli.py`: 新增 `production-run` 命令，调用 `ProductionRunner`。
- Modify `web_ui.py`: 新增长篇生产线 API，包括项目状态、dry-run 计划、启动生产。
- Modify `web_templates/index.html`: 新增长篇连载生产线模块，调用新 API 并展示计划/进度。
- Modify `web_file_catalog.py`: 文件清单继续覆盖 `novel_outputs`，必要时让 production run 产物显示更清楚。
- Create `tests/test_production_runner.py`: 覆盖停点、进度读写、dry-run、执行串联、失败停止。
- Modify `tests/test_llm_client.py`: 覆盖 MiniMax-M3 默认解析和 thinking 清理保持。
- Modify `tests/test_packager.py`: 覆盖按 run 目录打包。
- Modify `tests/test_cli.py`: 覆盖 `production-run` CLI 分发。
- Modify `tests/test_web_ui.py`: 覆盖新 API 和页面命令暴露。

---

### Task 1: Update MiniMax-M3 Model Slot

**Files:**
- Modify: `config.yaml`
- Modify: `core_engine/config_loader.py`
- Modify: `README.md`
- Modify: `tests/test_llm_client.py`

- [ ] **Step 1: Write failing config test**

Add this test to `tests/test_llm_client.py`:

```python
def test_default_model_slot_is_minimax_m3():
    from core_engine.config_loader import load_config, reset_config_cache

    reset_config_cache()
    cfg = load_config()
    resolved = resolve_model_config(cfg, "model_slot_1")

    assert resolved["slot_name"] == "model_slot_1"
    assert resolved["display_name"] == "MiniMax-M3"
    assert resolved["base_url"] == "https://api.minimaxi.com/v1"
    assert resolved["api_key_env"] == "MINIMAX_API_KEY"
    assert resolved["model_id"] == "MiniMax-M3"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_llm_client.py::test_default_model_slot_is_minimax_m3 -q`

Expected: FAIL because the current config still resolves `MiniMax-M2.7`.

- [ ] **Step 3: Update `config.yaml`**

Change the `llm` block and `models.slots.model_slot_1` block to:

```yaml
llm:
  model_slot: "model_slot_1"
  api_key_env: "MINIMAX_API_KEY"
  base_url: "https://api.minimaxi.com/v1"
  model: "MiniMax-M3"
  timeout: 300
  max_retries: 3
  strict_validation: true
  tools:
    web_search: false
    web_extractor: false
    code_interpreter: false
    file_search: false
    enable_thinking: false
```

```yaml
models:
  default_slot: "model_slot_1"
  slots:
    model_slot_1:
      display_name: "MiniMax-M3"
      base_url: "https://api.minimaxi.com/v1"
      api_key_env: "MINIMAX_API_KEY"
      model_id: "MiniMax-M3"
      enabled: true
      note: "MiniMax OpenAI 兼容接口，API Key 从本机 MINIMAX_API_KEY 环境变量读取。"
```

- [ ] **Step 4: Update `core_engine/config_loader.py` defaults**

In `_defaults()`, change `model_slot_1` and `llm.model` to:

```python
"model_slot_1": {
    "display_name": "MiniMax-M3",
    "base_url": "https://api.minimaxi.com/v1",
    "api_key_env": "MINIMAX_API_KEY",
    "model_id": "MiniMax-M3",
    "enabled": True,
    "note": "MiniMax OpenAI 兼容接口，API Key 从本机 MINIMAX_API_KEY 环境变量读取。",
},
```

```python
"llm": {
    "model_slot": DEFAULT_MODEL_SLOT,
    "api_key_env": "MINIMAX_API_KEY",
    "base_url": "https://api.minimaxi.com/v1",
    "model": "MiniMax-M3",
    "max_retries": 3,
    "timeout": 300,
    "enable_rag": False,
    "strict_validation": True,
    "tools": {
        "web_search": False,
        "web_extractor": False,
        "code_interpreter": False,
        "file_search": False,
        "enable_thinking": False,
    },
    "retry": {
        "base_delay_sec": 1.0,
        "max_delay_sec": 8.0,
        "jitter_sec": 0.25,
    },
},
```

- [ ] **Step 5: Update README model text**

Replace references to `MiniMax-M2.7` with `MiniMax-M3`, keeping the API key guidance as environment-variable-only:

```markdown
# model_slot_1 -> MINIMAX_API_KEY -> MiniMax-M3
$env:MINIMAX_API_KEY="sk-..."
```

Do not add a real key.

- [ ] **Step 6: Run focused tests**

Run: `python3 -m pytest tests/test_llm_client.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add config.yaml core_engine/config_loader.py README.md tests/test_llm_client.py
git commit -m "feat: switch default model slot to MiniMax-M3"
```

---

### Task 2: Add Production Runner Planning And Progress Models

**Files:**
- Create: `core_engine/production_runner.py`
- Create: `tests/test_production_runner.py`

- [ ] **Step 1: Write failing tests for default project and stop points**

Create `tests/test_production_runner.py` with:

```python
import json

from core_engine.production_runner import ProductionRunner


def test_default_project_plan_starts_with_chapters_1_to_3(tmp_path):
    runner = ProductionRunner(workspace_root=tmp_path)

    plan = runner.plan_run(project_id="sample_zerg_queen", dry_run=True)

    assert plan.project_id == "sample_zerg_queen"
    assert plan.chapter_indexes == [1, 2, 3]
    assert plan.chapter_titles == [
        "第一章：败局重启，女皇归巢",
        "第二章：第一枚血脉样本",
        "第三章：忍村边境的寄生眼",
    ]
    assert plan.stop_reason == "opening_review"
    assert plan.model_slot == "model_slot_1"

    project_path = tmp_path / "novel_outputs" / "production_runs" / "sample_zerg_queen" / "project.json"
    progress_path = tmp_path / "novel_outputs" / "production_runs" / "sample_zerg_queen" / "progress.json"
    assert project_path.exists()
    assert progress_path.exists()
    assert json.loads(progress_path.read_text(encoding="utf-8"))["next_chapter_index"] == 1


def test_stop_points_follow_opening_then_structural_units(tmp_path):
    runner = ProductionRunner(workspace_root=tmp_path)
    runner.ensure_project("sample_zerg_queen")

    progress = runner.load_progress("sample_zerg_queen")
    progress.last_completed_chapter_index = 3
    progress.next_chapter_index = 4
    runner.save_progress("sample_zerg_queen", progress)
    plan = runner.plan_run(project_id="sample_zerg_queen", dry_run=True)
    assert plan.chapter_indexes == [4, 5, 6]
    assert plan.stop_reason == "first_unit_completion"

    progress.last_completed_chapter_index = 6
    progress.next_chapter_index = 7
    runner.save_progress("sample_zerg_queen", progress)
    plan = runner.plan_run(project_id="sample_zerg_queen", dry_run=True)
    assert plan.chapter_indexes == [7, 8, 9, 10, 11, 12]
    assert plan.stop_reason == "unit_review_6"

    progress.last_completed_chapter_index = 18
    progress.next_chapter_index = 19
    runner.save_progress("sample_zerg_queen", progress)
    plan = runner.plan_run(project_id="sample_zerg_queen", dry_run=True)
    assert plan.chapter_indexes == [19, 20, 21, 22, 23, 24, 25]
    assert plan.stop_reason == "unit_review_7"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_production_runner.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'core_engine.production_runner'`.

- [ ] **Step 3: Implement planning models**

Create `core_engine/production_runner.py`:

```python
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_PROJECT_ID = "sample_zerg_queen"
DEFAULT_MODEL_SLOT = "model_slot_1"
UNIT_PATTERN = (6, 6, 6, 7)


@dataclass
class ProductionProject:
    project_id: str
    title: str
    genre: str
    author_name: str
    core_promise: str
    ip_policy: str
    first_world: str
    total_chapters: int = 400
    target_chars_per_chapter: int = 2500
    default_model_slot: str = DEFAULT_MODEL_SLOT
    chapter_title_seeds: Dict[str, str] = field(default_factory=dict)

    def project_bundle(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_title": self.title,
            "genre": self.genre,
            "core_promise": self.core_promise,
            "ip_policy": self.ip_policy,
            "first_world": self.first_world,
            "total_chapters": self.total_chapters,
            "target_chars_per_chapter": self.target_chars_per_chapter,
        }


@dataclass
class ProductionProgress:
    last_completed_chapter_index: int = 0
    next_chapter_index: int = 1
    current_volume: int = 1
    current_arc: int = 1
    current_unit: int = 1
    previous_chapter_writeback: str = "新书开局，败局重启，无上一章回写。"
    last_run_id: str = ""
    last_review_stop_point: str = ""
    state: str = "ready"


@dataclass
class ProductionPlan:
    project_id: str
    chapter_indexes: List[int]
    chapter_titles: List[str]
    stop_reason: str
    model_slot: str
    output_root: str
    dry_run: bool = True


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip()).strip("_")
    return slug or DEFAULT_PROJECT_ID


def _default_project(project_id: str = DEFAULT_PROJECT_ID) -> ProductionProject:
    return ProductionProject(
        project_id=_safe_slug(project_id),
        title="我，虫族女皇，带领虫族踏遍万界",
        genre="诸天万界流",
        author_name="默认作者",
        core_promise="败局重启的虫族女皇带领虫群进入原创影子世界，把每个世界变成虫族进化资源场。",
        ip_policy="只使用原创影子世界，不直接使用任何真实知名 IP 世界名。",
        first_world="忍术血脉世界",
        chapter_title_seeds={
            "1": "第一章：败局重启，女皇归巢",
            "2": "第二章：第一枚血脉样本",
            "3": "第三章：忍村边境的寄生眼",
            "4": "第四章：查克拉适配虫",
            "5": "第五章：暗部巡逻线",
            "6": "第六章：母巢第一次进化",
        },
    )


class ProductionRunner:
    def __init__(self, workspace_root: str | Path):
        self.workspace_root = Path(workspace_root)
        self.production_root = self.workspace_root / "novel_outputs" / "production_runs"

    def project_root(self, project_id: str) -> Path:
        return self.production_root / _safe_slug(project_id)

    def ensure_project(self, project_id: str = DEFAULT_PROJECT_ID) -> ProductionProject:
        root = self.project_root(project_id)
        root.mkdir(parents=True, exist_ok=True)
        project_path = root / "project.json"
        progress_path = root / "progress.json"
        if project_path.exists():
            project = ProductionProject(**json.loads(project_path.read_text(encoding="utf-8")))
        else:
            project = _default_project(project_id)
            project_path.write_text(json.dumps(asdict(project), ensure_ascii=False, indent=2), encoding="utf-8")
        if not progress_path.exists():
            self.save_progress(project.project_id, ProductionProgress())
        return project

    def load_progress(self, project_id: str) -> ProductionProgress:
        path = self.project_root(project_id) / "progress.json"
        if not path.exists():
            self.ensure_project(project_id)
        return ProductionProgress(**json.loads(path.read_text(encoding="utf-8")))

    def save_progress(self, project_id: str, progress: ProductionProgress) -> None:
        root = self.project_root(project_id)
        root.mkdir(parents=True, exist_ok=True)
        (root / "progress.json").write_text(
            json.dumps(asdict(progress), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def position_for_chapter(chapter_index: int) -> Dict[str, int]:
        zero_based = max(chapter_index - 1, 0)
        volume = zero_based // 100 + 1
        chapter_in_volume = zero_based % 100
        arc = chapter_in_volume // 25 + 1
        chapter_in_arc = chapter_in_volume % 25
        unit_edges = (6, 12, 18, 25)
        unit = next(index + 1 for index, edge in enumerate(unit_edges) if chapter_in_arc < edge)
        return {"volume": volume, "arc": arc, "unit": unit}

    @staticmethod
    def _default_count_and_reason(next_chapter_index: int) -> tuple[int, str]:
        if next_chapter_index == 1:
            return 3, "opening_review"
        if next_chapter_index == 4:
            return 3, "first_unit_completion"
        chapter_in_arc = (next_chapter_index - 1) % 25 + 1
        unit_starts = (1, 7, 13, 19)
        unit_lengths = (6, 6, 6, 7)
        for start, length in zip(unit_starts, unit_lengths):
            end = start + length - 1
            if start <= chapter_in_arc <= end:
                return end - chapter_in_arc + 1, f"unit_review_{length}"
        return 1, "chapter_review"

    def _chapter_title(self, project: ProductionProject, chapter_index: int) -> str:
        return project.chapter_title_seeds.get(str(chapter_index), f"第{chapter_index}章：虫群远征记录")

    def plan_run(
        self,
        project_id: str = DEFAULT_PROJECT_ID,
        chapters: Optional[int] = None,
        from_chapter: Optional[int] = None,
        model_slot: Optional[str] = None,
        dry_run: bool = True,
    ) -> ProductionPlan:
        project = self.ensure_project(project_id)
        progress = self.load_progress(project.project_id)
        start = from_chapter or progress.next_chapter_index
        default_count, stop_reason = self._default_count_and_reason(start)
        count = chapters or default_count
        indexes = list(range(start, min(start + count, project.total_chapters + 1)))
        return ProductionPlan(
            project_id=project.project_id,
            chapter_indexes=indexes,
            chapter_titles=[self._chapter_title(project, index) for index in indexes],
            stop_reason=stop_reason if chapters is None else "manual_chapter_count",
            model_slot=model_slot or project.default_model_slot,
            output_root=str(self.project_root(project.project_id)),
            dry_run=dry_run,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_production_runner.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core_engine/production_runner.py tests/test_production_runner.py
git commit -m "feat: add longform production planning"
```

---

### Task 3: Add Dry-Run Result And Run Directory Persistence

**Files:**
- Modify: `core_engine/production_runner.py`
- Modify: `tests/test_production_runner.py`

- [ ] **Step 1: Write failing dry-run persistence test**

Append to `tests/test_production_runner.py`:

```python
def test_dry_run_persists_run_config_and_summary_without_chapters(tmp_path):
    runner = ProductionRunner(workspace_root=tmp_path)

    result = runner.run(project_id="sample_zerg_queen", dry_run=True)

    run_root = tmp_path / "novel_outputs" / "production_runs" / "sample_zerg_queen" / "runs" / result.run_id
    assert result.ok is True
    assert result.dry_run is True
    assert (run_root / "run_config.json").exists()
    assert (run_root / "run_summary.json").exists()
    assert not (run_root / "chapters").exists()

    summary = json.loads((run_root / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["chapter_indexes"] == [1, 2, 3]
    assert summary["stop_reason"] == "opening_review"
    assert summary["next_action"] == "dry_run_only"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_production_runner.py::test_dry_run_persists_run_config_and_summary_without_chapters -q`

Expected: FAIL because `ProductionRunner.run` is not defined.

- [ ] **Step 3: Add run result model and dry-run method**

Add to `core_engine/production_runner.py` after `ProductionPlan`:

```python
@dataclass
class ProductionRunResult:
    ok: bool
    run_id: str
    project_id: str
    dry_run: bool
    chapter_indexes: List[int]
    stop_reason: str
    completed_chapters: List[int] = field(default_factory=list)
    failed_chapter: Optional[int] = None
    error: str = ""
    run_root: str = ""
    next_action: str = ""
```

Add these methods inside `ProductionRunner`:

```python
    @staticmethod
    def _new_run_id() -> str:
        return "run_" + datetime.now().strftime("%Y%m%d_%H%M%S")

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def run(
        self,
        project_id: str = DEFAULT_PROJECT_ID,
        chapters: Optional[int] = None,
        from_chapter: Optional[int] = None,
        model_slot: Optional[str] = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> ProductionRunResult:
        plan = self.plan_run(
            project_id=project_id,
            chapters=chapters,
            from_chapter=from_chapter,
            model_slot=model_slot,
            dry_run=dry_run,
        )
        run_id = self._new_run_id()
        run_root = self.project_root(plan.project_id) / "runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)

        run_config = {
            "run_id": run_id,
            "project_id": plan.project_id,
            "chapter_indexes": plan.chapter_indexes,
            "chapter_titles": plan.chapter_titles,
            "stop_reason": plan.stop_reason,
            "model_slot": plan.model_slot,
            "dry_run": dry_run,
            "force": force,
        }
        self._write_json(run_root / "run_config.json", run_config)

        if dry_run:
            result = ProductionRunResult(
                ok=True,
                run_id=run_id,
                project_id=plan.project_id,
                dry_run=True,
                chapter_indexes=plan.chapter_indexes,
                stop_reason=plan.stop_reason,
                run_root=str(run_root),
                next_action="dry_run_only",
            )
            self._write_json(run_root / "run_summary.json", asdict(result))
            return result

        raise RuntimeError("production execution is implemented in the execution task")
```

- [ ] **Step 4: Run focused test**

Run: `python3 -m pytest tests/test_production_runner.py::test_dry_run_persists_run_config_and_summary_without_chapters -q`

Expected: PASS.

- [ ] **Step 5: Run all production runner tests**

Run: `python3 -m pytest tests/test_production_runner.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core_engine/production_runner.py tests/test_production_runner.py
git commit -m "feat: persist production dry-run plans"
```

---

### Task 4: Implement Real Production Execution With Safe Chapter Chaining

**Files:**
- Modify: `core_engine/production_runner.py`
- Modify: `tests/test_production_runner.py`

- [ ] **Step 1: Write fake orchestrator tests for chapter chaining**

Append to `tests/test_production_runner.py`:

```python
from types import SimpleNamespace


class FakeOrchestrator:
    def __init__(self):
        self.calls = []
        self.llm_client = None

    def run_chapter(self, project_goal, chapter_input, model_id, output_root, write_files=True, verbose=True):
        self.calls.append(
            {
                "project_goal": project_goal,
                "chapter": chapter_input.current_chapter,
                "index": chapter_input.chapter_index,
                "previous": chapter_input.previous_chapter_writeback,
                "model_id": model_id,
                "output_root": str(output_root),
            }
        )
        return SimpleNamespace(
            project_id=chapter_input.project_bundle["project_id"],
            chapter_index=chapter_input.chapter_index,
            chapter_title=chapter_input.current_chapter,
            chapter_text=f"# {chapter_input.current_chapter}\n正文",
            stage_summaries={"stage_9": "已回写"},
            fanqie_quality_report={"is_valid": True, "score": 90},
            next_chapter_writeback={
                "source_chapter_index": chapter_input.chapter_index,
                "writeback_script": f"第{chapter_input.chapter_index}章回写",
            },
            output_files={},
        )


def test_real_run_chains_only_step_9_writeback(monkeypatch, tmp_path):
    fake = FakeOrchestrator()

    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test")
    monkeypatch.setattr("core_engine.production_runner.ChapterOrchestrator", lambda: fake)
    monkeypatch.setattr("core_engine.production_runner.LLMClient", lambda api_key, base_url: object())
    monkeypatch.setattr(
        "core_engine.production_runner.load_config",
        lambda: {
            "models": {
                "default_slot": "model_slot_1",
                "slots": {
                    "model_slot_1": {
                        "display_name": "MiniMax-M3",
                        "base_url": "https://api.minimaxi.com/v1",
                        "api_key_env": "MINIMAX_API_KEY",
                        "model_id": "MiniMax-M3",
                        "enabled": True,
                    }
                },
            },
            "llm": {},
        },
    )

    runner = ProductionRunner(workspace_root=tmp_path)
    result = runner.run(project_id="sample_zerg_queen", chapters=2)

    assert result.ok is True
    assert result.completed_chapters == [1, 2]
    assert fake.calls[0]["previous"] == "新书开局，败局重启，无上一章回写。"
    assert json.loads(fake.calls[1]["previous"]) == {
        "source_chapter_index": 1,
        "writeback_script": "第1章回写",
    }

    progress = runner.load_progress("sample_zerg_queen")
    assert progress.last_completed_chapter_index == 2
    assert progress.next_chapter_index == 3
    assert json.loads(progress.previous_chapter_writeback)["source_chapter_index"] == 2


def test_real_run_stops_on_orchestrator_failure(monkeypatch, tmp_path):
    class FailingOrchestrator(FakeOrchestrator):
        def run_chapter(self, *args, **kwargs):
            if len(self.calls) == 1:
                raise RuntimeError("stage_8_not_approved")
            return super().run_chapter(*args, **kwargs)

    fake = FailingOrchestrator()
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test")
    monkeypatch.setattr("core_engine.production_runner.ChapterOrchestrator", lambda: fake)
    monkeypatch.setattr("core_engine.production_runner.LLMClient", lambda api_key, base_url: object())
    monkeypatch.setattr(
        "core_engine.production_runner.load_config",
        lambda: {
            "models": {
                "default_slot": "model_slot_1",
                "slots": {
                    "model_slot_1": {
                        "display_name": "MiniMax-M3",
                        "base_url": "https://api.minimaxi.com/v1",
                        "api_key_env": "MINIMAX_API_KEY",
                        "model_id": "MiniMax-M3",
                        "enabled": True,
                    }
                },
            },
            "llm": {},
        },
    )

    runner = ProductionRunner(workspace_root=tmp_path)
    result = runner.run(project_id="sample_zerg_queen", chapters=3)

    assert result.ok is False
    assert result.completed_chapters == [1]
    assert result.failed_chapter == 2
    assert "stage_8_not_approved" in result.error
    assert runner.load_progress("sample_zerg_queen").next_chapter_index == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_production_runner.py::test_real_run_chains_only_step_9_writeback tests/test_production_runner.py::test_real_run_stops_on_orchestrator_failure -q`

Expected: FAIL because real execution still raises the placeholder runtime error.

- [ ] **Step 3: Add imports and model resolver helpers**

At the top of `core_engine/production_runner.py`, add:

```python
import os

from chapter_pipeline import ChapterOrchestrator, ChapterPipelineInput
from core_engine.config_loader import load_config, resolve_model_config
from core_engine.llm_client import LLMClient
```

Inside `ProductionRunner`, add:

```python
    def _resolve_model(self, model_slot: str) -> Dict[str, str]:
        cfg = load_config()
        model_cfg = resolve_model_config(cfg, model_slot)
        missing_fields = [
            field
            for field in ("base_url", "model_id", "api_key_env")
            if not str(model_cfg.get(field) or "").strip()
        ]
        if missing_fields:
            raise RuntimeError("missing_model_config:" + ",".join(missing_fields))
        api_key_env = str(model_cfg["api_key_env"])
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(f"missing_env:{api_key_env}")
        return {
            "slot_name": str(model_cfg["slot_name"]),
            "base_url": str(model_cfg["base_url"]),
            "model_id": str(model_cfg["model_id"]),
            "api_key_env": api_key_env,
            "api_key": api_key,
        }
```

- [ ] **Step 4: Replace the production branch in `run()`**

Replace:

```python
        raise RuntimeError("production execution is implemented in the execution task")
```

with:

```python
        project = self.ensure_project(plan.project_id)
        progress = self.load_progress(plan.project_id)
        model = self._resolve_model(plan.model_slot)
        orchestrator = ChapterOrchestrator()
        orchestrator.llm_client = LLMClient(api_key=model["api_key"], base_url=model["base_url"])
        completed: List[int] = []
        previous_writeback = progress.previous_chapter_writeback
        failed_chapter: Optional[int] = None
        error = ""

        chapters_root = run_root / "chapters"
        for chapter_index, chapter_title in zip(plan.chapter_indexes, plan.chapter_titles):
            position = self.position_for_chapter(chapter_index)
            try:
                chapter_input = ChapterPipelineInput(
                    project_bundle=project.project_bundle(),
                    current_chapter=chapter_title,
                    previous_chapter_writeback=previous_writeback,
                    local_kb_reference="正式长篇生产：本轮以项目包、当前章节和上一章第9步回写作为连续性主输入。",
                    search_summary="正式长篇生产：本轮不额外扩展跨章搜索摘要；如需联网资料，由章节编排器在章内按需处理。",
                    chapter_index=chapter_index,
                    model_slot=plan.model_slot,
                )
                output = orchestrator.run_chapter(
                    project_goal=f"{project.title} 正式长篇连载生产",
                    chapter_input=chapter_input,
                    model_id=model["model_id"],
                    output_root=chapters_root,
                    write_files=True,
                    verbose=True,
                )
                completed.append(chapter_index)
                previous_writeback = json.dumps(output.next_chapter_writeback, ensure_ascii=False)
                progress.last_completed_chapter_index = chapter_index
                progress.next_chapter_index = chapter_index + 1
                progress.previous_chapter_writeback = previous_writeback
                progress.current_volume = position["volume"]
                progress.current_arc = position["arc"]
                progress.current_unit = position["unit"]
                progress.last_run_id = run_id
                progress.last_review_stop_point = plan.stop_reason
                progress.state = "ready"
                self.save_progress(plan.project_id, progress)
            except Exception as exc:
                failed_chapter = chapter_index
                error = str(exc) or exc.__class__.__name__
                progress.next_chapter_index = chapter_index
                progress.state = "failed"
                progress.last_run_id = run_id
                self.save_progress(plan.project_id, progress)
                break

        ok = failed_chapter is None
        result = ProductionRunResult(
            ok=ok,
            run_id=run_id,
            project_id=plan.project_id,
            dry_run=False,
            chapter_indexes=plan.chapter_indexes,
            stop_reason=plan.stop_reason,
            completed_chapters=completed,
            failed_chapter=failed_chapter,
            error=error,
            run_root=str(run_root),
            next_action="review_packet" if ok else "repair_failed_chapter",
        )
        self._write_json(run_root / "run_summary.json", asdict(result))
        return result
```

- [ ] **Step 5: Run focused tests**

Run: `python3 -m pytest tests/test_production_runner.py::test_real_run_chains_only_step_9_writeback tests/test_production_runner.py::test_real_run_stops_on_orchestrator_failure -q`

Expected: PASS.

- [ ] **Step 6: Run all production runner tests**

Run: `python3 -m pytest tests/test_production_runner.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add core_engine/production_runner.py tests/test_production_runner.py
git commit -m "feat: execute production chapters with writeback chaining"
```

---

### Task 5: Generate Review Packets And Scoped Packages

**Files:**
- Modify: `core_engine/production_runner.py`
- Modify: `core_engine/packager.py`
- Modify: `tests/test_production_runner.py`
- Modify: `tests/test_packager.py`

- [ ] **Step 1: Write packager scoped-source test**

Append to `tests/test_packager.py`:

```python
def test_fanqie_packager_can_package_specific_chapter_root(tmp_path):
    source_root = tmp_path / "novel_outputs" / "production_runs" / "sample" / "runs" / "run_1" / "chapters"
    chapter_dir = source_root / "sample_zerg_queen" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "chapter.md").write_text("# 第一章\n正文", encoding="utf-8")
    (chapter_dir / "next_chapter_writeback.json").write_text(
        json.dumps({"source_chapter_index": 1}, ensure_ascii=False),
        encoding="utf-8",
    )
    (chapter_dir / "fanqie_quality_report.json").write_text(
        json.dumps({"score": 91}, ensure_ascii=False),
        encoding="utf-8",
    )

    zip_path = ProjectPackager(str(tmp_path)).create_fanqie_package(
        project_name="虫族女皇",
        genre="诸天万界流",
        author_name="默认作者",
        source_root=str(source_root),
        package_dir=str(tmp_path / "novel_outputs" / "production_runs" / "sample" / "runs" / "run_1" / "package"),
    )

    with zipfile.ZipFile(zip_path) as zipf:
        names = set(zipf.namelist())
        assert "02_正文分章/chapter_001.md" in names
        manifest = json.loads(zipf.read("00_打包清单/manifest.json").decode("utf-8"))
        assert manifest["source"] == str(source_root)
        assert manifest["chapter_count"] == 1
```

- [ ] **Step 2: Write review packet test**

Append to `tests/test_production_runner.py`:

```python
def test_review_packet_is_written_after_successful_run(monkeypatch, tmp_path):
    fake = FakeOrchestrator()
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test")
    monkeypatch.setattr("core_engine.production_runner.ChapterOrchestrator", lambda: fake)
    monkeypatch.setattr("core_engine.production_runner.LLMClient", lambda api_key, base_url: object())
    monkeypatch.setattr(
        "core_engine.production_runner.load_config",
        lambda: {
            "models": {
                "default_slot": "model_slot_1",
                "slots": {
                    "model_slot_1": {
                        "display_name": "MiniMax-M3",
                        "base_url": "https://api.minimaxi.com/v1",
                        "api_key_env": "MINIMAX_API_KEY",
                        "model_id": "MiniMax-M3",
                        "enabled": True,
                    }
                },
            },
            "llm": {},
        },
    )

    runner = ProductionRunner(workspace_root=tmp_path)
    result = runner.run(project_id="sample_zerg_queen", chapters=1)

    run_root = tmp_path / "novel_outputs" / "production_runs" / "sample_zerg_queen" / "runs" / result.run_id
    review = run_root / "review_packet" / "batch_review.md"
    continuity = run_root / "review_packet" / "continuity_report.json"
    assert review.exists()
    assert "第 1 章" in review.read_text(encoding="utf-8")
    assert json.loads(continuity.read_text(encoding="utf-8"))["completed_chapters"] == [1]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_packager.py::test_fanqie_packager_can_package_specific_chapter_root tests/test_production_runner.py::test_review_packet_is_written_after_successful_run -q`

Expected: FAIL because scoped packager parameters and review packet generation are not implemented.

- [ ] **Step 4: Modify `core_engine/packager.py` signatures and helpers**

Change method signatures and collection helpers:

```python
    def _chapter_files_from_novel_outputs(self, source_root: str | None = None) -> list[str]:
        root = source_root or self.novel_output_dir
        pattern = os.path.join(root, "*", "chapter_*", "chapter.md")
        return sorted(glob.glob(pattern))

    def _collect_writebacks(self, source_root: str | None = None) -> list[dict]:
        writebacks = []
        root = source_root or self.novel_output_dir
        pattern = os.path.join(root, "*", "chapter_*", "next_chapter_writeback.json")
        for path in sorted(glob.glob(pattern)):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except Exception:
                payload = {"source": path, "error": "read_failed"}
            writebacks.append(payload)
        return writebacks

    def _collect_quality_reports(self, source_root: str | None = None) -> list[tuple[str, str]]:
        reports = []
        root = source_root or self.novel_output_dir
        pattern = os.path.join(root, "*", "chapter_*", "fanqie_quality_report.json")
        for path in sorted(glob.glob(pattern)):
            reports.append((path, self._read_text(path)))
        return reports
```

Change `create_fanqie_package` signature and first lines:

```python
    def create_fanqie_package(
        self,
        project_name: str,
        genre: str,
        author_name: str,
        source_root: str | None = None,
        package_dir: str | None = None,
    ) -> str:
        """输出番茄小说投稿/存稿结构 ZIP。"""
        target_package_dir = package_dir or self.package_dir
        os.makedirs(target_package_dir, exist_ok=True)

        date_str = datetime.now().strftime("%Y%m%d")
        zip_name = f"【{genre}】{project_name}_{author_name}_番茄小说存稿包_{date_str}.zip"
        zip_path = os.path.join(target_package_dir, zip_name)

        chapter_files = self._chapter_files_from_novel_outputs(source_root)
        writebacks = self._collect_writebacks(source_root)
        quality_reports = self._collect_quality_reports(source_root)
```

Set manifest source to:

```python
            "source": source_root or "novel_outputs",
```

- [ ] **Step 5: Add review packet methods to `ProductionRunner`**

Add inside `ProductionRunner`:

```python
    def _write_review_packet(
        self,
        run_root: Path,
        result: ProductionRunResult,
        chapter_titles: List[str],
    ) -> None:
        review_dir = run_root / "review_packet"
        review_dir.mkdir(parents=True, exist_ok=True)
        lines = [
            "# 批次审稿包",
            "",
            f"- 项目: {result.project_id}",
            f"- 运行: {result.run_id}",
            f"- 停点: {result.stop_reason}",
            f"- 已完成章节: {', '.join(str(item) for item in result.completed_chapters) or '无'}",
            f"- 失败章节: {result.failed_chapter or '无'}",
            "",
            "## 章节状态",
            "",
        ]
        for chapter_index, title in zip(result.chapter_indexes, chapter_titles):
            status = "完成" if chapter_index in result.completed_chapters else "未完成"
            lines.append(f"- 第 {chapter_index} 章：{title}：{status}")
        lines.extend(
            [
                "",
                "## 下一步建议",
                "",
                "- 若本批口感、设定边界和章尾钩子通过人工审稿，继续下一停点。",
                "- 若存在第8步不放行或连续性风险，先修复失败章节，再恢复生产。",
            ]
        )
        (review_dir / "batch_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._write_json(
            review_dir / "continuity_report.json",
            {
                "project_id": result.project_id,
                "run_id": result.run_id,
                "completed_chapters": result.completed_chapters,
                "failed_chapter": result.failed_chapter,
                "stop_reason": result.stop_reason,
            },
        )
        (review_dir / "next_batch_suggestions.md").write_text(
            "# 下一批建议\n\n通过人工审稿后，从 progress.json 的 next_chapter_index 继续生产。\n",
            encoding="utf-8",
        )
```

Before writing `run_summary.json` in the non-dry-run branch, call:

```python
        self._write_review_packet(run_root, result, plan.chapter_titles)
```

- [ ] **Step 6: Run focused tests**

Run: `python3 -m pytest tests/test_packager.py::test_fanqie_packager_can_package_specific_chapter_root tests/test_production_runner.py::test_review_packet_is_written_after_successful_run -q`

Expected: PASS.

- [ ] **Step 7: Run related tests**

Run: `python3 -m pytest tests/test_packager.py tests/test_production_runner.py -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add core_engine/packager.py core_engine/production_runner.py tests/test_packager.py tests/test_production_runner.py
git commit -m "feat: add production review packets and scoped packaging"
```

---

### Task 6: Add CLI `production-run`

**Files:**
- Modify: `scripts/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI dispatch tests**

Append to `tests/test_cli.py`:

```python
def test_cli_production_run_dispatches_to_runner(monkeypatch, capsys):
    calls = {}

    class FakeResult:
        ok = True
        run_id = "run_test"
        project_id = "sample_zerg_queen"
        dry_run = True
        chapter_indexes = [1, 2, 3]
        stop_reason = "opening_review"
        completed_chapters = []
        failed_chapter = None
        error = ""
        run_root = "/tmp/run_test"
        next_action = "dry_run_only"

    class FakeRunner:
        def __init__(self, workspace_root):
            calls["workspace_root"] = workspace_root

        def run(self, **kwargs):
            calls.update(kwargs)
            return FakeResult()

    monkeypatch.setattr(cli, "ProductionRunner", FakeRunner, raising=False)

    exit_code = cli.main([
        "production-run",
        "--project",
        "sample_zerg_queen",
        "--chapters",
        "3",
        "--model-slot",
        "model_slot_1",
        "--dry-run",
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert calls["project_id"] == "sample_zerg_queen"
    assert calls["chapters"] == 3
    assert calls["model_slot"] == "model_slot_1"
    assert calls["dry_run"] is True
    assert "run_test" in output


def test_cli_production_run_returns_failure_exit(monkeypatch):
    class FakeResult:
        ok = False
        run_id = "run_failed"
        project_id = "sample_zerg_queen"
        dry_run = False
        chapter_indexes = [1]
        stop_reason = "opening_review"
        completed_chapters = []
        failed_chapter = 1
        error = "missing_env:MINIMAX_API_KEY"
        run_root = "/tmp/run_failed"
        next_action = "repair_failed_chapter"

    class FakeRunner:
        def __init__(self, workspace_root):
            pass

        def run(self, **kwargs):
            return FakeResult()

    monkeypatch.setattr(cli, "ProductionRunner", FakeRunner, raising=False)

    assert cli.main(["production-run", "--project", "sample_zerg_queen"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cli.py::test_cli_production_run_dispatches_to_runner tests/test_cli.py::test_cli_production_run_returns_failure_exit -q`

Expected: FAIL because the CLI has no `production-run` command.

- [ ] **Step 3: Add import and command helper**

At the top of `scripts/cli.py`, after imports, add:

```python
try:
    from core_engine.production_runner import ProductionRunner
except Exception:  # pragma: no cover - import errors surface when command runs
    ProductionRunner = None  # type: ignore[assignment]
```

Add helper before `build_parser()`:

```python
def _production_run_command(
    project_id: str,
    chapters: Optional[int],
    from_chapter: Optional[int],
    model_slot: Optional[str],
    dry_run: bool,
    force: bool,
) -> int:
    if ProductionRunner is None:
        print("❌ 长篇连载生产控制器不可用。")
        return 1
    runner = ProductionRunner(_get_workspace())
    result = runner.run(
        project_id=project_id,
        chapters=chapters,
        from_chapter=from_chapter,
        model_slot=model_slot,
        dry_run=dry_run,
        force=force,
    )
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    return 0 if result.ok else 1
```

- [ ] **Step 4: Add parser command**

Inside `build_parser()`, before hidden legacy commands, add:

```python
    production_parser = subparsers.add_parser("production-run", help="长篇连载生产线：按停点生成章节并产出审稿包")
    production_parser.add_argument("--project", default="sample_zerg_queen", help="项目 ID，默认虫族女皇正式生产预设")
    production_parser.add_argument("--chapters", type=int, help="本轮手动生成章数，默认跑到下一停点")
    production_parser.add_argument("--from-chapter", type=int, help="从指定章节开始修复或恢复")
    production_parser.add_argument("--model-slot", help="模型槽位，默认使用项目配置")
    production_parser.add_argument("--dry-run", action="store_true", help="只展示并落盘本轮计划，不调用模型")
    production_parser.add_argument("--force", action="store_true", help="允许显式修复或覆盖已有章节")
```

Inside `main()`, before `search-diagnose`, add:

```python
    if args.command == "production-run":
        return _production_run_command(
            project_id=args.project,
            chapters=args.chapters,
            from_chapter=args.from_chapter,
            model_slot=args.model_slot,
            dry_run=args.dry_run,
            force=args.force,
        )
```

- [ ] **Step 5: Run focused CLI tests**

Run: `python3 -m pytest tests/test_cli.py::test_cli_production_run_dispatches_to_runner tests/test_cli.py::test_cli_production_run_returns_failure_exit -q`

Expected: PASS.

- [ ] **Step 6: Run all CLI tests**

Run: `python3 -m pytest tests/test_cli.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/cli.py tests/test_cli.py
git commit -m "feat: add production-run cli command"
```

---

### Task 7: Add Web API For Longform Production

**Files:**
- Modify: `web_ui.py`
- Modify: `tests/test_web_ui.py`

- [ ] **Step 1: Write failing API tests**

Append to `tests/test_web_ui.py`:

```python
def test_production_status_api_returns_plan(monkeypatch, tmp_path):
    class FakePlan:
        project_id = "sample_zerg_queen"
        chapter_indexes = [1, 2, 3]
        chapter_titles = ["第一章", "第二章", "第三章"]
        stop_reason = "opening_review"
        model_slot = "model_slot_1"
        output_root = str(tmp_path)
        dry_run = True

    class FakeRunner:
        def __init__(self, workspace_root):
            assert workspace_root == web_ui.BASE_DIR

        def plan_run(self, project_id, model_slot=None, dry_run=True):
            return FakePlan()

    monkeypatch.setattr(web_ui, "ProductionRunner", FakeRunner, raising=False)

    import asyncio

    payload = asyncio.run(web_ui.production_status())

    assert payload["ok"] is True
    assert payload["plan"]["chapter_indexes"] == [1, 2, 3]
    assert payload["plan"]["stop_reason"] == "opening_review"


def test_production_start_api_dispatches_runner(monkeypatch):
    calls = {}

    class FakeResult:
        ok = True
        run_id = "run_web"
        project_id = "sample_zerg_queen"
        dry_run = True
        chapter_indexes = [1, 2, 3]
        stop_reason = "opening_review"
        completed_chapters = []
        failed_chapter = None
        error = ""
        run_root = "/tmp/run_web"
        next_action = "dry_run_only"

    class FakeRunner:
        def __init__(self, workspace_root):
            pass

        def run(self, **kwargs):
            calls.update(kwargs)
            return FakeResult()

    class FakeRequest:
        async def json(self):
            return {"project_id": "sample_zerg_queen", "model_slot": "model_slot_1", "dry_run": True}

    monkeypatch.setattr(web_ui, "ProductionRunner", FakeRunner, raising=False)

    import asyncio

    payload = asyncio.run(web_ui.production_start(FakeRequest()))

    assert payload["ok"] is True
    assert payload["result"]["run_id"] == "run_web"
    assert calls["project_id"] == "sample_zerg_queen"
    assert calls["model_slot"] == "model_slot_1"
    assert calls["dry_run"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_web_ui.py::test_production_status_api_returns_plan tests/test_web_ui.py::test_production_start_api_dispatches_runner -q`

Expected: FAIL because the API handlers are not defined.

- [ ] **Step 3: Add import and serializer**

In `web_ui.py`, add near imports:

```python
try:
    from core_engine.production_runner import ProductionRunner
except Exception:  # pragma: no cover
    ProductionRunner = None  # type: ignore[assignment]
```

Add helper after `_model_options()`:

```python
def _dataclass_payload(value: Any) -> Dict[str, Any]:
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    if isinstance(value, dict):
        return dict(value)
    return {"value": value}
```

- [ ] **Step 4: Add API routes**

Add after `/api/orchestrator-status`:

```python
@app.get("/api/production/status")
async def production_status():
    if ProductionRunner is None:
        return _command_result(ok=False, error="长篇连载生产控制器不可用。", command="production_status")
    runner = ProductionRunner(BASE_DIR)
    plan = runner.plan_run(project_id="sample_zerg_queen", dry_run=True)
    return _command_result(
        ok=True,
        command="production_status",
        plan=_dataclass_payload(plan),
    )


@app.post("/api/production/start")
async def production_start(request: Request):
    if ProductionRunner is None:
        return _command_result(ok=False, error="长篇连载生产控制器不可用。", command="production_start")
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    runner = ProductionRunner(BASE_DIR)
    result = runner.run(
        project_id=str(payload.get("project_id") or "sample_zerg_queen"),
        chapters=payload.get("chapters"),
        from_chapter=payload.get("from_chapter"),
        model_slot=str(payload.get("model_slot") or "").strip() or None,
        dry_run=bool(payload.get("dry_run", False)),
        force=bool(payload.get("force", False)),
    )
    return _command_result(
        ok=bool(result.ok),
        command="production_start",
        result=_dataclass_payload(result),
        error=getattr(result, "error", ""),
    )
```

- [ ] **Step 5: Run focused API tests**

Run: `python3 -m pytest tests/test_web_ui.py::test_production_status_api_returns_plan tests/test_web_ui.py::test_production_start_api_dispatches_runner -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web_ui.py tests/test_web_ui.py
git commit -m "feat: add production runner web api"
```

---

### Task 8: Add Web UI Longform Production Panel

**Files:**
- Modify: `web_templates/index.html`
- Modify: `web_ui.py`
- Modify: `tests/test_web_ui.py`

- [ ] **Step 1: Write dashboard exposure test**

Append to `tests/test_web_ui.py`:

```python
def test_dashboard_exposes_longform_production_section():
    section = next(section for section in web_ui.DASHBOARD_SECTIONS if section["id"] == "longform_production")
    command_ids = {command["id"] for command in section["commands"]}

    assert section["title"] == "长篇连载生产线"
    assert "production_status" in command_ids
    assert "production_dry_run" in command_ids
    assert "production_start" in command_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_web_ui.py::test_dashboard_exposes_longform_production_section -q`

Expected: FAIL because the dashboard section is missing.

- [ ] **Step 3: Add dashboard section**

In `web_ui.py`, add this object to `DASHBOARD_SECTIONS` near the chapter production section:

```python
    {
        "id": "longform_production",
        "title": "长篇连载生产线",
        "class": "module-longform",
        "description": "正式长篇生产控制器：每章完整九步，按 1-3、4-6、6/6/6/7 停点审稿。",
        "commands": [
            {"id": "production_status", "label": "查看生产计划", "kind": "production_status"},
            {"id": "production_dry_run", "label": "Dry Run", "kind": "production_dry_run"},
            {"id": "production_start", "label": "启动正式生产", "kind": "production_start"},
        ],
    },
```

- [ ] **Step 4: Update template styles**

In `web_templates/index.html`, add CSS next to other module colors:

```css
        .module-longform {
            background: #e8f6f3;
        }
```

- [ ] **Step 5: Update front-end command handling**

In the existing JavaScript command handler, route the three production command IDs to:

```javascript
async function runProductionCommand(commandId) {
    const modelSlot = document.getElementById("model-select")?.value || "";
    const payload = {
        project_id: "sample_zerg_queen",
        model_slot: modelSlot
    };
    let url = "/api/production/status";
    let options = { method: "GET" };
    if (commandId === "production_dry_run") {
        url = "/api/production/start";
        payload.dry_run = true;
        options = {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        };
    }
    if (commandId === "production_start") {
        url = "/api/production/start";
        payload.dry_run = false;
        options = {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        };
    }
    const response = await fetch(url, options);
    const data = await response.json();
    appendLog(JSON.stringify(data, null, 2));
}
```

Then ensure click handling calls `runProductionCommand(commandId)` when `commandId` is one of `production_status`, `production_dry_run`, or `production_start`.

- [ ] **Step 6: Run dashboard test**

Run: `python3 -m pytest tests/test_web_ui.py::test_dashboard_exposes_longform_production_section -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add web_ui.py web_templates/index.html tests/test_web_ui.py
git commit -m "feat: expose longform production panel"
```

---

### Task 9: Final Verification And Documentation

**Files:**
- Modify: `README.md`
- Modify: `TODO.md`
- Run verification commands

- [ ] **Step 1: Update README production section**

Add this section near CLI usage:

```markdown
### 长篇连载生产线

正式生产入口使用每章完整九步母版，外层按审稿停点暂停：

```bash
python -m scripts.cli production-run --project sample_zerg_queen --dry-run
python -m scripts.cli production-run --project sample_zerg_queen --model-slot model_slot_1
```

默认策略：
- 第 1-3 章完成后暂停审稿。
- 第 4-6 章完成后暂停审稿。
- 后续按每弧内 `6 / 6 / 6 / 7` 结构单元暂停。

`model_slot_1` 默认使用 `MiniMax-M3`，API Key 只从本机 `MINIMAX_API_KEY` 环境变量读取。
```

- [ ] **Step 2: Update TODO.md with new completed section**

Append:

```markdown
## 9. 长篇连载生产线

- [x] 将默认 MiniMax 模型槽位更新为 `MiniMax-M3`。
- [x] 新增长篇连载生产控制器，支持项目预设、进度、停点和审稿包。
- [x] 新增 CLI `production-run`，以 dry-run 作为工程验收基线。
- [x] 新增网页控制台长篇连载生产线入口。
- [x] 保持每章独立执行完整九步母版，只用上一章第9步回写续接下一章。
```

- [ ] **Step 3: Run focused test groups**

Run:

```bash
python3 -m pytest tests/test_llm_client.py tests/test_production_runner.py tests/test_packager.py tests/test_cli.py tests/test_web_ui.py -q
```

Expected: PASS.

- [ ] **Step 4: Run full test suite**

Run:

```bash
python3 -m pytest -q
```

Expected: PASS.

- [ ] **Step 5: Run dry-run command manually**

Run:

```bash
python3 -m scripts.cli production-run --project sample_zerg_queen --dry-run
```

Expected: JSON output with:

```json
{
  "ok": true,
  "project_id": "sample_zerg_queen",
  "dry_run": true,
  "chapter_indexes": [1, 2, 3],
  "stop_reason": "opening_review"
}
```

- [ ] **Step 6: Check for accidental API key literals**

Run:

```bash
rg -n "sk-[A-Za-z0-9]|api_key\\s*[:=]\\s*[\"'][^\"']+[\"']|MINIMAX_API_KEY=.*" .
```

Expected: no real API key values. Test strings such as `sk-test` are acceptable only inside tests.

- [ ] **Step 7: Commit final docs**

```bash
git add README.md TODO.md
git commit -m "docs: document longform production runner"
```

---

## Self-Review

Spec coverage:

- MiniMax-M3 model slot: Task 1.
- Shared production core: Tasks 2-5.
- CLI entry: Task 6.
- Web API and UI: Tasks 7-8.
- Output directory, progress, run summary: Tasks 2-3.
- Step 9 writeback-only chaining: Task 4.
- Review packet and scoped package: Task 5.
- API key environment-only rule: Tasks 1 and 9.

Placeholder scan:

- No unfinished marker phrases are intentionally left in this plan.
- Every task has exact file paths, commands, expected results, and code blocks for changed behavior.

Type consistency:

- `ProductionRunner.plan_run()` returns `ProductionPlan`.
- `ProductionRunner.run()` returns `ProductionRunResult`.
- CLI and web tests serialize result objects through `__dict__`.
- Project ID defaults consistently to `sample_zerg_queen`.

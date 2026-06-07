# Longform Production Runner Design

## 1. Purpose

This design turns the project into a formal longform webnovel production tool for a 1,000,000+ word serial. The system must support a 400 chapter book, around 2,500 Chinese characters per chapter, while preserving the existing `《红星锚定》九步章节生产线完整母版 v2.2.md` as the chapter-level production unit.

The default production preset is:

- Title: `我，虫族女皇，带领虫族踏遍万界`
- Genre: `诸天万界流`
- Core promise: a reborn Zerg queen leads her swarm through original shadow worlds and turns each world into an evolutionary resource field.
- Opening stance: defeat-and-restart.
- Protagonist style: elegant, dangerous, charismatic, and unstable in a controlled way.
- IP policy: use original shadow worlds only. The first world is a `忍术血脉世界`, not a direct named IP world.
- Default model: `model_slot_1 -> MINIMAX_API_KEY -> MiniMax-M3`.

All model API keys must be read from local environment variables only. No key may be written into code, docs, config examples, logs, or generated artifacts.

## 2. Core Correction From Brainstorming

The nine-step master template is not a batch-generation template. It is the formal single-chapter construction unit.

The production runner must not compress multiple chapters into one prompt or one model conversation. Each chapter is an isolated run that executes the full nine-step pipeline:

1. Chapter variable extraction
2. Input card
3. Ontology tree plus ToT path expansion
4. X/Y double-line pruning
5. Six-beat construction table
6. Two-beat drafting plus six single-factor iterations
7. Reader-side review and commercial revision
8. Evidence-based exit gate
9. Minimal next-chapter navigation script

Chapter continuity is passed only through the previous chapter's step 9 navigation script. The runner must not pass the full previous chapter text into the next chapter.

## 3. Production Cadence

The runner produces one chapter per chapter-level round. The outer serial controller decides how many chapter rounds to execute before pausing for review.

Default stop points:

- Opening exploration: run chapters 1-3, then pause.
- First unit completion: run chapters 4-6, then pause.
- Stable production: pause at the end of each structural unit using the existing `6 / 6 / 6 / 7` pattern inside every 25-chapter arc.
- Arc review: every 25 chapters.
- Volume review: every 100 chapters.

The default mode must be conservative. The system should stop early when a chapter fails a hard gate, rather than continue a damaged serial chain.

Manual overrides may allow a user to run a chosen chapter count, but the default experience should preserve the stop-point strategy above.

## 4. Shared Architecture

Add a shared production core, tentatively named `core_engine/production_runner.py`. CLI and web UI should call this shared core instead of duplicating orchestration logic.

Primary responsibilities:

- Load project metadata and progress.
- Resolve the model slot.
- Validate required environment variables.
- Decide the next production stop point.
- Build the chapter queue for this run.
- Call the existing `ChapterOrchestrator.run_chapter` once per chapter.
- Pass only the previous chapter step 9 writeback to the next chapter.
- Persist progress after each successful chapter.
- Generate a review packet when the run reaches a stop point.
- Return structured status for CLI and web UI.

The existing chapter orchestrator remains responsible for the nine-step chapter pipeline. The production runner only coordinates serial longform progress around it.

## 5. CLI Design

Add a command:

```bash
python -m scripts.cli production-run --project sample_zerg_queen
```

Default behavior:

- Use the default project preset if the project does not exist yet.
- Resolve `model_slot_1` unless the user passes `--model-slot`.
- Continue from `progress.json`.
- Run to the next default stop point.
- Stop on the first hard failure.
- Write run outputs under the production run directory.

Useful options:

- `--chapters N`: run a specific number of chapters instead of the default stop point.
- `--from-chapter N`: start at a specific chapter when the user intentionally resumes or repairs.
- `--model-slot SLOT`: override the model slot.
- `--dry-run`: show the production plan and write no chapter content.
- `--force`: allow a repair run over an existing chapter after explicit user intent.

The CLI is the regression baseline for production behavior.

## 6. Web UI Design

Add a `长篇连载生产线` section to the web console.

The web UI should support:

- Select project.
- Select model slot.
- Display current longform position: volume, arc, unit, chapter.
- Display next run plan: chapter range and stop reason.
- Start production through the shared production runner.
- Show current run status: chapter, stage, retry count, failure reason, and next step.
- Open chapter artifacts: chapter text, quality report, execution plan, stage summaries, and step 9 writeback.
- Open the batch review packet and package output.

The web layer should not implement its own production logic. It should expose API routes that call the same shared runner used by CLI.

## 7. Data And Output Layout

Formal longform production outputs should live outside ad hoc demo output:

```text
novel_outputs/
  production_runs/
    sample_zerg_queen/
      project.json
      progress.json
      runs/
        run_YYYYMMDD_HHMMSS/
          run_config.json
          run_summary.json
          chapters/
            chapter_001/
              chapter.md
              stage_summaries.json
              fanqie_quality_report.json
              next_chapter_writeback.json
              execution_plan.json
          review_packet/
            batch_review.md
            continuity_report.json
            next_batch_suggestions.md
          package/
            fanqie_submission_package.zip
```

`project.json` stores:

- Book metadata.
- Original-shadow-world policy.
- Longform structure.
- Default model slot.
- Preset chapter title seeds where available.

`progress.json` stores:

- Last completed chapter index.
- Next chapter index.
- Current volume, arc, and unit.
- Previous chapter step 9 writeback.
- Last run ID.
- Last review stop point.
- Current production state.

`run_summary.json` stores:

- Run ID.
- Chapter range.
- Model slot and resolved model ID.
- Stop reason.
- Completed chapters.
- Failed chapter, if any.
- Output paths.
- Next recommended action.

Progress should be authoritative. The runner should not infer the current chapter by scanning folders.

## 8. Chapter Gates And Failure Handling

The runner should fail early and visibly.

Hard failures:

- Missing required model key environment variable.
- Missing model `base_url`, `model_id`, or `api_key_env`.
- Empty model output.
- Thinking content remains in persisted chapter text after cleanup.
- Stage 6A or any Stage 6B round fails.
- Stage 8 returns `不放行`.
- Stage 9 is missing, not usable for the next chapter, or outside the 150-250 character target.
- A chapter output is missing required artifacts.

Risk states:

- Stage 7 does not identify at least one repairable issue.
- Stage 8 returns `带风险放行`.
- Validator report flags continuity, hook, pacing, or AI-tone warnings.

Risk states should appear in the review packet and web UI. Hard failures stop the run.

## 9. MiniMax-M3 Model Configuration

Update `model_slot_1` to:

- Display name: `MiniMax-M3`
- Base URL: `https://api.minimaxi.com/v1`
- API key environment variable: `MINIMAX_API_KEY`
- Model ID: `MiniMax-M3`

The client should keep chapter text clean:

- Prefer request settings that prevent thinking content from being mixed into normal output when supported by the provider.
- Continue stripping `<think>...</think>` blocks from returned text.
- Treat cleaned-empty output as a failure.

The implementation should not store API keys in `config.yaml`, README, tests, docs, logs, or artifacts.

## 10. Review Packet Design

At every stop point, generate a review packet for the author.

The packet should include:

- Chapters included in the run.
- Chapter-level status table.
- Word count summary.
- Step 8 exit-gate summary.
- Step 9 continuity chain summary.
- New pits, filled pits, and unresolved pits.
- Main payoff state per chapter.
- Continuity risks.
- Setting overload risks.
- AI-tone and pacing risks.
- Recommended next run range.

The review packet is not a replacement for chapter-level steps 7 and 8. It is the outer author review layer for longform production.

## 11. Acceptance Criteria

Engineering acceptance:

- `model_slot_1` resolves to MiniMax-M3.
- `production-run --dry-run` returns the correct next stop point without calling a real model.
- The production runner persists `project.json`, `progress.json`, `run_config.json`, and `run_summary.json`.
- The runner can plan chapters 1-3, 4-6, and later `6 / 6 / 6 / 7` unit stop points.
- CLI and web UI both call the shared production runner.
- Web UI can display project progress, next run plan, latest run summary, and artifact links.
- Tests verify that API keys are referenced only by environment variable names.

Production acceptance:

- With `MINIMAX_API_KEY` present, the user can start the default project with MiniMax-M3.
- The first run produces chapters 1-3 and stops for review.
- Each completed chapter contains chapter text, quality report, execution plan, stage summaries, and step 9 writeback.
- Chapter 2 receives only chapter 1 step 9 writeback as continuity input.
- Chapter 3 receives only chapter 2 step 9 writeback as continuity input.
- A batch review packet is generated at the stop point.

## 12. Non-Goals

This design does not:

- Rewrite the nine-step master template.
- Generate multiple chapters inside one model conversation.
- Add a new multi-agent framework.
- Rework Brave or Tavily search strategy.
- Split PreHub into M01-M09 agent steps.
- Automatically generate all 400 chapters in one command by default.
- Use direct names from existing third-party IP worlds in formal production output.


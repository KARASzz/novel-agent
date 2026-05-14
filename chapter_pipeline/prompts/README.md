# 九步章节生产线提示词资产

提示词原文已经内置到 `chapter_pipeline/prompt_registry.py`。

`chapter_pipeline.prompt_registry.ChapterPromptRegistry` 直接从代码常量读取以下 prompt block：

- `redstar_nine_step_chapter_pipeline_v2_2`
- `stage_1_chapter_variable_extraction`
- `stage_2_input_card`
- `stage_3_ontology_tree_and_tot`
- `stage_4_xy_pruning`
- `stage_5_six_beat_construction_table`
- `stage_6a_draft_two_beats`
- `stage_6b_single_factor_iteration`
- `stage_7_reader_review_and_commercial_revision`
- `stage_8_evidence_exit_gate`
- `stage_9_chapter_navigation_script`

运行时不要再从根目录母版 Markdown 抽取提示词。后续修改提示词时，直接维护 `prompt_registry.py` 中的代码内置常量。

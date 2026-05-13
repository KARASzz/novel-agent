# 九步章节生产线提示词资产

提示词原文以根目录 `《红星锚定》九步章节生产线完整母版 v2.2.md` 为唯一来源。

`chapter_pipeline.prompt_registry.ChapterPromptRegistry` 会按 XML 标签原样抽取以下 prompt block：

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

不要在这里维护第二份手工拷贝，避免母版和工程提示词发生漂移。

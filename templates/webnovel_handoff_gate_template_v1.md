# 网文大纲中台交接闸门模板 v1.0

> 用途：检查“大纲 -> 设定集 -> 卷故事清单 -> 施工卡 -> 九步第1步”的交接是否干净。  
> 边界：只验收交接，不写大纲、不写设定、不写正文。

---

## 0. 使用规则

```yaml
file_role: handoff_gate_template
priority: context_control
source_chain:
  - NovelMacroOutline
  - NovelSettingBible
  - VolumeStoryList
  - ChapterConstructionCard
  - stage_1_chapter_variable_extraction
cannot_do:
  - 修改正文
  - 修改九步第2-9步
  - 放行整份大纲进入单章生产线
  - 放行整份设定集进入单章生产线
```

---

# 第一部分：产物链检查

```yaml
artifact_chain_gate:
  outline_exists: true/false
  outline_uses_template: "templates/webnovel_outline_template_v1.md"
  setting_bible_exists: true/false
  setting_bible_uses_template: "templates/webnovel_setting_bible_template_v1.md"
  volume_story_list_exists: true/false
  chapter_construction_card_exists: true/false
  previous_stage_9_writeback_exists_or_first_chapter_exception: true/false
```

---

# 第二部分：结构检查

```yaml
structure_gate:
  total_chapters: 400
  volumes: 4
  chapters_per_volume: 100
  arcs_per_volume: 4
  chapters_per_arc: 25
  unit_pattern: [6, 6, 6, 7]
  six_chapter_unit_distribution: [1, 2, 2, 1]
  seven_chapter_unit_distribution: [1, 2, 2, 2]
```

---

# 第三部分：单章上下文检查

```yaml
single_chapter_context_gate:
  one_chapter_only: true/false
  current_chapter_matches_story_list: true/false
  current_chapter_matches_construction_card: true/false
  active_rules_count_lte_2: true/false
  active_terms_count_lte_2: true/false
  active_characters_count_lte_3: true/false
  active_location_single: true/false
  visible_consequence_exists: true/false
  cliffhanger_exists: true/false
```

---

# 第四部分：污染检查

```yaml
pollution_gate:
  no_full_outline_dump: true/false
  no_full_setting_bible_dump: true/false
  no_whole_volume_story_list_dump: true/false
  no_future_chapter_body: true/false
  no_stage_2_direct_generation: true/false
  no_stage_5_or_6_prewrite: true/false
```

---

# 第五部分：九步第1步交接

只允许交给第1步以下内容：

```yaml
stage_1_allowed_payload:
  current_chapter: ""
  chapter_construction_card:
    chapter_index: 1
    structural_position: {}
    two_sentence_summary: []
    core_event: ""
    visible_consequence: ""
    cliffhanger: ""
    must_not_write: []
  chapter_setting_payload:
    active_rules: []
    active_terms: []
    active_characters: []
    active_location: ""
    aesthetic_payload: {}
  previous_chapter_script: ""
```

---

# 第六部分：最终判定

```yaml
handoff_gate_result:
  final_status: "通过 / 带风险通过 / 不通过"
  blocking_issues:
    - ""
  required_actions:
    - ""
  can_enter_stage_1: true/false
  can_enter_stage_2_directly: false
```

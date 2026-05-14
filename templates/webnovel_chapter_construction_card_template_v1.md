# 网文章级施工卡模板 v1.0

> 用途：把“大纲 + 设定集 + 本卷故事清单 + 上一章回写”压缩为单章任务书。  
> 边界：施工卡不写正文，不替代九步章节生产线，只作为第1步接口输入。  
> 下游：现有九步流程第1步“章节变量自动抽取”。

---

## 0. 使用规则

```yaml
file_role: chapter_construction_card_template
output_contract: ChapterConstructionCard
priority: current_chapter_task
must_feed_into: "stage_1_chapter_variable_extraction"
cannot_do:
  - 写正文
  - 写六节拍
  - 直接生成第2步输入卡
  - 把整份大纲塞入当前章
  - 把整份设定集塞入当前章
```

---

# 第一部分：章节定位

```yaml
chapter_identity:
  project_id: ""
  current_chapter: ""
  chapter_index: 1
  volume_id: 1
  volume_title: ""
  arc_id: 1
  arc_function: "起 / 承 / 转 / 合"
  unit_id: 1
  unit_chapter_index: 1
  unit_chapter_count: 6
  structural_function: "起 / 承 / 转 / 合"
```

---

# 第二部分：两句话概括

```yaml
two_sentence_summary:
  event_progression: ""
  state_change_or_hook: ""
```

---

# 第三部分：本章施工目标

```yaml
chapter_task:
  core_event: ""
  chapter_goal: ""
  protagonist_action: ""
  character_state_change: ""
  information_change: ""
  rule_or_system_change: ""
  visible_consequence: ""
  payoff_type: "信息爽点 / 权力爽点 / 清算爽点 / 规则爽点 / 情绪爽点 / 格局爽点"
  cliffhanger: ""
```

---

# 第四部分：本章设定抽取

```yaml
chapter_setting_payload:
  active_rules: []        # 最多2条
  active_terms: []        # 最多2个
  active_characters: []   # 最多3个
  active_location: ""
  required_visible_consequence: ""
  aesthetic_payload:
    objects: []
    sounds: []
    body_signals: []
    system_or_rule_feedback: []
```

---

# 第五部分：禁止事项

```yaml
must_not_write:
  - ""
  - ""
  - ""
```

---

# 第六部分：上一章承接

```yaml
previous_chapter_handoff:
  previous_chapter_index: 0
  previous_stage_9_writeback: ""
  must_continue:
    - ""
  unresolved_hooks:
    - ""
  forbidden_skip:
    - ""
```

---

# 第七部分：第1步交接包

```yaml
nine_step_stage_1_payload:
  current_chapter: ""
  chapter_construction_card: "本文件"
  chapter_setting_payload: "第四部分"
  previous_chapter_script: "上一章第9步回写"
```

---

# 第八部分：施工卡放行检查

```yaml
chapter_card_gate:
  one_chapter_only: true/false
  has_two_sentence_summary: true/false
  has_core_event: true/false
  has_visible_consequence: true/false
  has_cliffhanger: true/false
  active_rules_count_lte_2: true/false
  active_terms_count_lte_2: true/false
  active_characters_count_lte_3: true/false
  no_full_outline_dump: true/false
  no_full_setting_bible_dump: true/false
  final_status: "通过 / 带风险通过 / 不通过"
```

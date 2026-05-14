# 网文分卷极简故事清单模板 v1.0

> 用途：给每个卷Agent输出本卷100章的极简故事清单。  
> 边界：每章只写两句话概括，不写施工卡，不写正文。  
> 上游：`templates/webnovel_outline_template_v1.md`、`templates/webnovel_setting_bible_template_v1.md`。

---

## 0. 使用规则

```yaml
file_role: volume_story_list_template
output_contract: VolumeStoryList
volume_count: 4
chapters_per_volume: 100
arcs_per_volume: 4
chapters_per_arc: 25
units_per_arc: 4
unit_chapter_pattern: [6, 6, 6, 7]
six_chapter_unit_function_pattern: [起, 承, 承, 转, 转, 合]
seven_chapter_unit_function_pattern: [起, 承, 承, 转, 转, 合, 合]
cannot_do:
  - 写正文
  - 写章级施工卡
  - 改写全书大纲
  - 改写设定集锁定项
```

---

# 第一部分：卷Agent信息

```yaml
volume_agent:
  agent_id: "volume_1_story_agent / volume_2_story_agent / volume_3_story_agent / volume_4_story_agent"
  volume_id: 1
  volume_title: ""
  chapter_range: "1-100 / 101-200 / 201-300 / 301-400"
  source_outline: "templates/webnovel_outline_template_v1.md产物"
  source_setting_bible: "templates/webnovel_setting_bible_template_v1.md产物"
  output_contract: "VolumeStoryList"
```

---

# 第二部分：本卷目标

```yaml
volume_story_goal:
  stage_goal: ""
  protagonist_state_start: ""
  protagonist_state_end: ""
  main_pressure: ""
  volume_payoff: ""
  cost_paid: ""
  next_volume_hook: ""
  must_not_write:
    - ""
```

---

# 第三部分：四个故事弧

| 弧序 | 章节范围 | 弧功能 | 小目标 | 阻碍 | 关键反转 | 爽点 | 代价 | 弧尾钩子 |
|---:|---|---|---|---|---|---|---|---|
| 1 | 1-25 | 起 |  |  |  |  |  |  |
| 2 | 26-50 | 承 |  |  |  |  |  |  |
| 3 | 51-75 | 转 |  |  |  |  |  |  |
| 4 | 76-100 | 合 |  |  |  |  |  |  |

---

# 第四部分：故事单元结构

每个故事弧固定4个故事单元：

| 单元序 | 章数 | 起承转合分配 | 单元目标 | 单元爆点 | 单元尾钩子 |
|---:|---:|---|---|---|---|
| 1 | 6 | 1-2-2-1 |  |  |  |
| 2 | 6 | 1-2-2-1 |  |  |  |
| 3 | 6 | 1-2-2-1 |  |  |  |
| 4 | 7 | 1-2-2-2 |  |  |  |

---

# 第五部分：100章极简故事清单

> 每章只写两句话。  
> 第一句：事件推进。  
> 第二句：状态变化、可见后果或章尾钩子。

| 全书章号 | 卷内章号 | 弧 | 单元 | 功能 | 两句话概括 |
|---:|---:|---:|---:|---|---|
| 1 | 1 | 1 | 1 | 起 | 事件推进：。状态变化/钩子：。 |
| 2 | 2 | 1 | 1 | 承 | 事件推进：。状态变化/钩子：。 |
| 3 | 3 | 1 | 1 | 承 | 事件推进：。状态变化/钩子：。 |
| 4 | 4 | 1 | 1 | 转 | 事件推进：。状态变化/钩子：。 |
| 5 | 5 | 1 | 1 | 转 | 事件推进：。状态变化/钩子：。 |
| 6 | 6 | 1 | 1 | 合 | 事件推进：。状态变化/钩子：。 |

---

# 第六部分：放行检查

```yaml
volume_story_list_gate:
  exactly_100_chapters: true/false
  four_arcs_each_25_chapters: true/false
  unit_pattern_is_6_6_6_7: true/false
  every_chapter_has_two_sentences: true/false
  no_chapter_body: true/false
  no_outline_rewrite: true/false
  no_setting_bible_rewrite: true/false
  final_status: "通过 / 带风险通过 / 不通过"
```

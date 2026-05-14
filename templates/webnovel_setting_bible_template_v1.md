# 网文设定集通用模板 v1.0

> 用途：给网文写作流水线提供“设定仓库”。  
> 定位：记录世界规则、人物连续性、势力结构、美学口感、术语边界。  
> 边界：设定集不直接写正文；每章只能抽取必要设定进入输入卡。  
> 适用类型：科幻、玄幻、都市、历史、权谋、悬疑、无限流、诸天流、系统流、群像文。

---

## 0. 使用规则

```yaml
file_role: setting_bible_template
priority: world_and_continuity_repository
can_decide:
  - 世界基础规则
  - 核心机制边界
  - 势力关系
  - 人物知情范围
  - 术语解释
  - 美学素材
  - 伏笔和连续性状态
cannot_decide:
  - 单章具体正文
  - 单章节拍顺序
  - 临场台词
  - 强行覆盖大纲主线
  - 无限扩写无冲突设定
```

### 调用原则

```text
设定集是仓库。
输入卡是工具箱。
章节生产是工地。
每章不能背仓库上工地。
```

---

# 第一部分：世界宪法

## 1. 世界一句话

```text
这是一个__________的世界。
在这个世界里，__________决定人的命运，
而主角将因为__________被卷入核心冲突。
```

---

## 2. 类型边界

```yaml
world_type: "架空 / 近未来 / 远未来 / 异世界 / 都市异能 / 历史架空 / 无限流 / 诸天流 / 其他"
tech_or_power_level: "低 / 中 / 高 / 超高"
realism_level: "写实 / 半写实 / 浪漫化 / 神话化 / 游戏化"
violence_level: "低 / 中 / 高"
romance_level: "无 / 弱 / 中 / 强"
humor_level: "无 / 弱 / 中 / 强"
reader_interface: "爽文 / 悬疑 / 权谋 / 升级 / 群像 / 情绪流 / 混合"
```

---

## 3. 世界红线

```yaml
must_keep:
  - ""
  - ""
must_not_write:
  - ""
  - ""
forbidden_old_versions:
  - ""
  - ""
safety_or_platform_limits:
  - ""
  - ""
```

---

# 第二部分：核心规则卡

## 4. 规则卡总表

| 规则名 | 类型 | 首次出现 | 读者可理解等级 | 当前状态 |
|---|---|---:|---|---|
|  | 能力/协议/科技/法术/职业/组织规则/诅咒/系统 |  | 直觉级/解释级/建构级/过载级 | 草案/锁定/修改中/废弃 |

---

## 5. 单条规则卡模板

```yaml
rule_card:
  name: ""
  type: "能力 / 协议 / 科技 / 法术 / 制度 / 地理 / 经济 / 文化 / 其他"
  one_sentence_definition: ""
  can_do:
    - ""
  cannot_do:
    - ""
  trigger_condition:
    - ""
  authority_or_usage_boundary:
    - ""
  cost:
    - ""
  failure_condition:
    - ""
  misuse_path:
    - ""
  who_knows:
    - ""
  who_misunderstands:
    - ""
  visible_consequence:
    - ""
  first_reveal_scene: ""
  forbidden_writing:
    - ""
  status: "草案 / 锁定 / 修改中 / 废弃"
```

### 规则卡检查

```yaml
rule_gate:
  has_boundary: true/false
  has_cost: true/false
  has_failure: true/false
  has_visible_consequence: true/false
  can_create_conflict: true/false
  not_omnipotent: true/false
```

---

# 第三部分：世界结构

## 6. 时空背景

```yaml
setting_background:
  era: ""
  geography: ""
  social_order: ""
  dominant_conflict: ""
  ordinary_life: ""
  public_truth: ""
  hidden_truth: ""
```

---

## 7. 社会层级

| 层级 | 人群 | 资源 | 限制 | 对主角意义 | 可见物件/场景 |
|---|---|---|---|---|---|
| 上层 |  |  |  |  |  |
| 中层 |  |  |  |  |  |
| 底层 |  |  |  |  |  |
| 边缘层 |  |  |  |  |  |

---

## 8. 经济与资源

```yaml
resources:
  core_resource: ""
  who_controls_it: ""
  how_people_get_it: ""
  scarcity_pressure: ""
  black_market_or_hidden_flow: ""
  plot_usage: ""
```

---

## 9. 技术 / 法术 / 能力体系

| 名称 | 能做 | 不能做 | 代价 | 使用门槛 | 谁掌握 | 剧情用途 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

---

# 第四部分：势力与机构

## 10. 势力总览

| 势力 | 表面目标 | 真实目标 | 核心资源 | 行动方式 | 与主角关系 | 内部矛盾 |
|---|---|---|---|---|---|---|
|  |  |  |  |  | 敌/友/中立/摇摆 |  |

---

## 11. 单势力卡

```yaml
faction:
  name: ""
  public_identity: ""
  true_function: ""
  leader_or_representative: ""
  core_interest: ""
  resources:
    - ""
  methods:
    - ""
  fear:
    - ""
  internal_split:
    - ""
  relationship_with_protagonist: ""
  first_visible_action: ""
  volume_usage: ""
  failure_or_change: ""
```

---

## 12. 权限 / 等级 / 职务表

| 等级/职务 | 能做 | 不能做 | 上级 | 下级 | 常见误判 | 剧情风险 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

---

# 第五部分：地图与场景

## 13. 地点总览

| 地点 | 类型 | 首次出现 | 功能 | 气味/声音/物件 | 关联人物 | 剧情用途 |
|---|---|---:|---|---|---|---|
|  | 城市/宗门/基地/街区/宫殿/学校/地下区/虚拟空间 |  |  |  |  |  |

---

## 14. 场景卡模板

```yaml
location:
  name: ""
  type: ""
  first_appearance: ""
  visual_anchor:
    - ""
  sound_anchor:
    - ""
  smell_or_texture:
    - ""
  social_rule: ""
  hidden_layer: ""
  conflict_potential: ""
  usable_events:
    - ""
  forbidden_cliche:
    - ""
```

---

# 第六部分：人物连续性账本

## 15. 人物总表

| 人物 | 身份 | 欲望 | 恐惧 | 资源 | 知情范围 | 误判 | 状态 |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  | 未登场/登场/失踪/死亡/转阵营 |

---

## 16. 主角卡

```yaml
protagonist:
  name: ""
  public_identity: ""
  hidden_identity_or_value: ""
  initial_desire: ""
  deeper_need: ""
  fear: ""
  stubborn_prediction: "他无论遇到什么证据，都会优先相信什么？"
  default_action: "这个信念被触发后，他第一反应会做什么？"
  collapse_threshold: "什么事件会让旧反应不够用？"
  useful_skill_or_position: ""
  boundary:
    can_do: []
    cannot_do: []
  growth_path:
    early: ""
    middle: ""
    late: ""
  recurring_objects:
    - ""
  language_features:
    - ""
```

---

## 17. 重要人物卡

```yaml
character:
  name: ""
  role: "主角 / 反派 / 配角 / 导师 / 对手 / 队友 / 关键工具人 / 群像人物"
  public_identity: ""
  private_truth: ""
  desire: ""
  fear: ""
  resource: ""
  wound_or_history: ""
  stubborn_prediction: ""
  default_action: ""
  collapse_threshold: ""
  knows:
    - ""
  does_not_know:
    - ""
  misunderstands:
    - ""
  relationship_with_protagonist: ""
  first_scene_function: ""
  later_function: ""
  exit_or_transformation: ""
```

---

## 18. 人物知情表

| 事件/秘密 | 主角知道 | 反派知道 | 配角A知道 | 公众知道 | 读者知道 | 备注 |
|---|---|---|---|---|---|---|
|  | 是/否/半知 | 是/否/半知 | 是/否/半知 | 是/否/半知 | 是/否/半知 |  |

---

# 第七部分：术语与认知负荷

## 19. 核心术语表

| 术语 | 一句话解释 | 等级 | 首次出现 | 正文处理方式 | 是否锁定 |
|---|---|---|---:|---|---|
|  |  | 直觉级/解释级/建构级/过载级 |  | 直接用/一句解释/场景演示/推迟 | 是/否 |

---

## 20. 认知可达性规则

```yaml
cognitive_load_rules:
  max_new_terms_per_chapter: 2
  max_constructive_terms_per_chapter: 1
  overload_terms_must_delay: true
  explanation_after_need: true
  demonstration_before_encyclopedia: true
```

---

# 第八部分：美学基座

## 21. 美学一句话

```text
本书的画面、声音、气味和物件应该给读者一种：__________。
```

---

## 22. 美学四层

| 层 | 本书定义 | 可用素材 | 禁止写法 |
|---|---|---|---|
| 视觉 |  |  |  |
| 听觉 |  |  |  |
| 气味/触感 |  |  |  |
| 象征 |  |  |  |

---

## 23. 物件池

```yaml
objects:
  daily_objects:
    - ""
  power_objects:
    - ""
  emotional_objects:
    - ""
  danger_objects:
    - ""
  recurring_symbols:
    - ""
```

---

## 24. 声音池

```yaml
sounds:
  daily_sounds:
    - ""
  system_sounds:
    - ""
  danger_sounds:
    - ""
  silence_patterns:
    - ""
```

---

## 25. 身体信号池

```yaml
body_signals:
  fear:
    - ""
  anger:
    - ""
  fatigue:
    - ""
  guilt:
    - ""
  decision_pressure:
    - ""
```

---

## 26. 语言禁区

```yaml
forbidden_phrases_or_tones:
  - "命运的齿轮开始转动"
  - "真正的风暴才刚刚开始"
  - "他终于意识到"
  - "巨大的阴谋"
  - "权力机器开始转动"
  - ""
replacement_principle: "用动作、物件、时间、流程、后果替代抽象总结。"
```

---

# 第九部分：时间线与事件账本

## 27. 主时间线

| 时间点 | 真实事件 | 公开口径 | 主角知道 | 其他势力知道 | 读者知道 | 后果 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

---

## 28. 卷内事件账本

| 章节 | 事件 | 信息变化 | 规则状态 | 人物状态 | 可见后果 | 下章承接 |
|---:|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |

---

# 第十部分：伏笔、回声与状态

## 29. 伏笔账本

| 伏笔 | 类型 | 埋设章节 | 推进章节 | 兑现章节 | 当前状态 | 风险 |
|---|---|---:|---:|---:|---|---|
|  | 信息/物件/人物/规则/台词/场景 |  |  |  | 未埋/已埋/推进中/已兑现/废弃 |  |

---

## 30. 回声账本

| 回声源 | 首次出现 | 回响章节 | 变化 | 情绪/意义 | 是否过度解释 |
|---|---:|---:|---|---|---|
|  |  |  |  |  | 是/否 |

---

## 31. 规则状态账本

| 规则 | 初始状态 | 当前状态 | 最近变化 | 是否写穿 | 修复动作 |
|---|---|---|---|---|---|
|  |  |  |  | 是/否/风险 |  |

---

# 第十一部分：章节生产接口

## 32. 从设定集抽取输入卡

每章只允许抽取：

```yaml
chapter_setting_payload:
  active_rules: []        # 最多2条
  active_terms: []        # 最多2个
  active_characters: []   # 最多3个
  active_location: ""
  required_visible_consequence: ""
  forbidden_writing: []
  aesthetic_payload:
    objects: []
    sounds: []
    body_signals: []
    system_or_rule_feedback: []
```

---

## 33. 章节接口检查

```yaml
chapter_payload_gate:
  active_rules_count_lte_2: true/false
  active_terms_count_lte_2: true/false
  no_overload_term: true/false
  visible_consequence_exists: true/false
  protagonist_boundary_clear: true/false
  no_worldview_dump: true/false
```

---

# 第十二部分：废案与版本管理

## 34. 废弃设定索引

| 废弃项 | 原因 | 替代方案 | 是否禁止回捞 |
|---|---|---|---|
|  |  |  | 是/否 |

---

## 35. 版本记录

| 版本 | 日期 | 修改内容 | 修改原因 | 是否影响已写章节 |
|---|---|---|---|---|
| v1.0 |  | 初版 | 通用设定集模板 | 否 |

---

# 第十三部分：设定集放行检查

```yaml
setting_bible_gate:
  core_rules_have_boundaries: true/false
  factions_have_conflict: true/false
  protagonist_boundary_clear: true/false
  terms_are_limited: true/false
  aesthetic_assets_exist: true/false
  timeline_has_public_and_true_versions: true/false
  continuity_ledgers_exist: true/false
  no_dead_encyclopedia_sections: true/false
  top_three_risks:
    - ""
    - ""
    - ""
  final_status: "通过 / 带风险通过 / 不通过"
```

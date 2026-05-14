# 网文长篇大纲通用模板 v1.0

> 用途：给网文写作流水线提供“全书骨架”。  
> 定位：决定这本书“卖什么、推什么、怎么分卷、爽点怎么释放”。  
> 边界：不写正文，不替代章节生产线，不扩写设定百科。  
> 适用类型：科幻、玄幻、都市、历史、悬疑、诸天、无限流、权谋、系统流、群像等长篇连载。

---

## 0. 使用规则

```yaml
file_role: outline_template
priority: commercial_structure
can_decide:
  - 书名方向
  - 简介卖点
  - 全书主线
  - 黄金三章目标
  - 分卷结构
  - 爽点释放节奏
  - 主要人物功能
cannot_decide:
  - 单章正文
  - 单章具体节拍
  - 设定细节无限扩写
  - 人物临场台词
  - 章节是否放行
```

### 三条硬规则

1. 每个设定必须能产生冲突。  
2. 每卷必须有明确目标、阻碍、代价、爆点。  
3. 大纲只写会影响主线的内容，其余交给设定集或章节生产线。

---

# 第一部分：项目商业定位

## 1. 项目元信息

```yaml
project_name: ""
working_title: ""
target_platform: "起点 / 番茄 / 七猫 / 晋江 / 微信读书 / 其他"
main_genre: ""
sub_genres: []
target_reader: ""
target_word_count: ""
expected_volume_count: ""
update_rhythm: ""
comparison_titles: []
forbidden_comparisons: []
```

---

## 2. 一句话前提 Logline

### 2.1 通用公式

```text
一名【主角身份】，为了【核心目标】，必须面对【最大阻碍】，
依靠/卷入【独特类型元素】，但每次推进都会付出【不可逆代价】。
```

### 2.2 填写区

```text
一名__________，
为了__________，
必须__________，
依靠/卷入__________，
但每次__________都会__________。
```

### 2.3 检查

```yaml
checks:
  clear_identity: true/false
  clear_goal: true/false
  clear_obstacle: true/false
  unique_element: true/false
  irreversible_cost: true/false
  can_pitch_in_10_seconds: true/false
```

---

## 3. 卖点包装

### 3.1 书名候选

| 类型 | 候选 | 优点 | 风险 |
|---|---|---|---|
| 直给型 |  |  |  |
| 悬念型 |  |  |  |
| 身份型 |  |  |  |
| 意象型 |  |  |  |
| 爽点型 |  |  |  |

### 3.2 标签

```yaml
main_tag: ""
reader_tags: []
plot_tags: []
selling_tags: []
risk_tags: []
```

### 3.3 简介三段式

```text
【困境】
主角处境 + 世界压力 + 第一矛盾。

【异变】
主角获得/卷入的独特机制 + 边界或代价。

【爽点预告】
主角将如何撬动局面 + 中后期最大期待。
```

### 3.4 简介压测

```yaml
first_three_sentences_have_conflict: true/false
hook_visible_before_100_words: true/false
no_empty_grand_words: true/false
no_worldview_dump: true/false
reader_knows_why_follow: true/false
```

---

# 第二部分：故事发动机

## 4. 主角发动机

```yaml
protagonist:
  name: ""
  initial_identity: ""
  initial_disadvantage: ""
  core_desire: ""
  visible_goal_first_30_chapters: ""
  hidden_need: ""
  fear_or_avoidance: ""
  useful_trait: ""
  fatal_flaw: ""
  growth_direction: ""
```

### 判断

```text
主角不是“设定容器”。
他必须因为欲望、恐惧、误判或责任被迫行动。
```

---

## 5. 独特机制 / 金手指 / 核心玩法

> 不限定为系统、外挂或能力。也可以是身份、规则、协议、信息位置、诅咒、职业、制度暗门、空间、血脉、技术、组织授权。

```yaml
core_mechanism:
  name: ""
  acquisition_or_trigger: ""
  one_sentence_function: ""
  can_do: []
  cannot_do: []
  upgrade_or_escalation_path: ""
  cost: ""
  failure_condition: ""
  visible_payoff: ""
  abuse_risk: ""
```

### 边界检查

```yaml
not_omnipotent: true/false
cost_is_real: true/false
payoff_is_visible: true/false
failure_can_happen: true/false
reader_can_understand_in_one_scene: true/false
```

---

## 6. 三线冲突

| 线 | 定义 | 本书填写 | 作用 | 失败风险 |
|---|---|---|---|---|
| 明线 | 每章可见的直接冲突 |  | 推动日常剧情 |  |
| 暗线 | 后期揭露的结构性冲突 |  | 扩大全书格局 |  |
| 内线 | 主角自身撕裂 |  | 支撑人物成长 |  |

### 检查

```text
明线负责追读。
暗线负责格局。
内线负责人物不空。
三线不能互相替代。
```

---

# 第三部分：黄金三章

## 7. 黄金三章总目标

```yaml
golden_three_chapters:
  chapter_1_goal: "让读者知道主角是谁、困境是什么、异常如何刺入"
  chapter_2_goal: "让机制开始运行，给出第一次可见回报"
  chapter_3_goal: "让机制造成不可逆后果，抛出下一阶段钩子"
  total_risk: ""
```

---

## 8. 第一章模板：钩子 + 身份 + 异常刺入

```yaml
chapter_1:
  opening_hook: ""
  protagonist_status: ""
  current_pressure: ""
  first_abnormal_event: ""
  world_info_limit: "最多3个必要名词"
  visible_payoff: ""
  ending_state_change: ""
  cliffhanger: ""
  must_not_write: []
```

---

## 9. 第二章模板：机制运行 + 小回报

```yaml
chapter_2:
  carry_over_from_ch1: ""
  mechanism_demonstration: ""
  protagonist_action: ""
  outside_reaction: ""
  first_small_payoff: ""
  new_information: ""
  ending_state_change: ""
  cliffhanger: ""
  must_not_write: []
```

---

## 10. 第三章模板：不可逆后果 + 大钩子

```yaml
chapter_3:
  starting_pressure: ""
  escalation_event: ""
  protagonist_decision_or_failure: ""
  visible_consequence: ""
  irreversible_change: ""
  larger_threat_or_mystery: ""
  ending_state_change: ""
  cliffhanger: ""
  must_not_write: []
```

---

# 第四部分：全书结构

## 11. 分卷总览

| 卷序 | 卷名 | 字数范围 | 阶段目标 | 主冲突 | 卷末爆点 | 下一卷钩子 |
|---|---|---:|---|---|---|---|
| 1 |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |

---

## 12. 单卷结构模板

```yaml
volume:
  volume_id: ""
  volume_title: ""
  word_count_range: ""
  stage_goal: ""
  protagonist_state_start: ""
  protagonist_state_end: ""
  main_enemy_or_pressure: ""
  core_location_or_institution: ""
  new_rule_or_mechanism: ""
  midpoint_turn: ""
  volume_payoff: ""
  cost_paid: ""
  unresolved_hook: ""
```

---

## 13. 故事弧模板

| 弧段 | 章节范围 | 小目标 | 阻碍 | 关键反转 | 爽点 | 代价 | 章末钩子 |
|---|---|---|---|---|---|---|---|
| 起 |  |  |  |  |  |  |  |
| 承 |  |  |  |  |  |  |  |
| 转 |  |  |  |  |  |  |  |
| 合 |  |  |  |  |  |  |  |

---

# 第五部分：人物功能

## 14. 核心人物表

| 人物 | 身份 | 欲望 | 恐惧 | 资源 | 弱点 | 与主角关系 | 剧情功能 | 首次登场 |
|---|---|---|---|---|---|---|---|---|
| 主角 |  |  |  |  |  |  |  |  |
| 主要反派 |  |  |  |  |  |  |  |  |
| 配角1 |  |  |  |  |  |  |  |  |
| 配角2 |  |  |  |  |  |  |  |  |
| 配角3 |  |  |  |  |  |  |  |  |

---

## 15. 反派/对手模板

```yaml
antagonist:
  name: ""
  public_identity: ""
  true_goal: ""
  why_they_think_they_are_right: ""
  power_base: ""
  method: ""
  blind_spot: ""
  conflict_with_protagonist: ""
  first_visible_pressure: ""
  defeat_or_transformation: ""
```

---

# 第六部分：爽点与期待管理

## 16. 爽点类型定义

```yaml
payoff_types:
  - information_payoff: "获得关键真相"
  - power_payoff: "能力、身份、权限或资源提升"
  - justice_payoff: "打脸、复仇、清算、曝光"
  - rule_payoff: "规则反向生效，卡住强者"
  - emotion_payoff: "关系确认、牺牲、和解、背叛"
  - scale_payoff: "地图、组织、格局升级"
```

---

## 17. 爽点节奏表

| 周期 | 类型 | 标准 | 本书设计 | 风险 |
|---|---|---|---|---|
| 每3—5章 | 小爽点 | 可见信息/资源/反击 |  |  |
| 每10—15章 | 中爽点 | 身份变化/小势力崩塌/规则升级 |  |  |
| 每卷末 | 大爽点 | 阶段清算/世界观翻转/强敌倒下 |  |  |
| 全书终局 | 终极爽点 | 核心矛盾解决或代价兑现 |  |  |

---

## 18. 期待账本

| 伏笔/期待 | 埋设章节 | 读者以为 | 真相 | 兑现章节 | 兑现方式 | 状态 |
|---|---:|---|---|---:|---|---|
|  |  |  |  |  |  | 未埋/已埋/推进中/已兑现/废弃 |

---

# 第七部分：风险控制

## 19. 常见致命问题

| 风险 | 症状 | 修复 |
|---|---|---|
| 主角是剧情容器 | 事件推着走，但主角没选择 | 给主角欲望、恐惧、误判或代价 |
| 设定百科化 | 名词连续出现，正文没事件 | 每章新概念≤2个，设定必须撞出后果 |
| 机制万能 | 什么问题都能一键解决 | 写清不能做、失败条件、代价 |
| 爽点不外化 | 作者说爽，读者看不见 | 写成文件退回、敌人失误、资源变化、状态变化 |
| 反派降智 | 只为衬托主角 | 给反派信息边界、合理误判和真实资源 |
| 前三章钩子弱 | 异常太晚，回报太迟 | 500字内给异常或压迫，3章内给可见后果 |
| 伏笔烂尾 | 只埋不填 | 建立期待账本，给兑现章节 |

---

## 20. 大纲放行检查

```yaml
outline_gate:
  logline_clear: true/false
  protagonist_active: true/false
  core_mechanism_bounded: true/false
  golden_three_chapters_have_state_change: true/false
  three_conflict_lines_exist: true/false
  volume_goals_clear: true/false
  payoff_schedule_exists: true/false
  setting_not_overwritten: true/false
  top_three_risks:
    - ""
    - ""
    - ""
  final_status: "通过 / 带风险通过 / 不通过"
```

---

# 第八部分：给章节生产线的接口

## 21. 章节输入接口

每章进入生产线前，只抽取以下内容：

```yaml
chapter_interface:
  current_chapter: ""
  previous_state: ""
  chapter_goal: ""
  must_not_happen: []
  active_mechanism: ""
  active_characters: []
  visible_payoff: ""
  cliffhanger_target: ""
```

### 禁止

```text
不要把整份大纲塞进单章生产。
每章只带本章需要的信息。
```

---

## 22. 版本记录

| 版本 | 日期 | 修改内容 | 修改原因 |
|---|---|---|---|
| v1.0 |  | 初版 | 通用大纲模板 |

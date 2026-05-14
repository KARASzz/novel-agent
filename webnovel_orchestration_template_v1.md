# 网文大纲中台编排模板 v1.0

> 用途：定义“立项 -> 大纲 -> 设定集 -> 分卷故事清单 -> 章级施工卡 -> 九步章节生产线”的中台流程。  
> 边界：本模板不写正文，不替代《红星锚定》九步章节生产线完整母版 v2.2。  
> 上游模板：`webnovel_outline_template_v1.md`、`webnovel_setting_bible_template_v1.md`。

---

## 0. 使用规则

```yaml
file_role: webnovel_orchestration_template
priority: process_and_agent_boundary
source_templates:
  - webnovel_outline_template_v1.md
  - webnovel_setting_bible_template_v1.md
must_preserve:
  - 现有九步章节生产线第2-9步
  - 第6A两节拍正文
  - 第6B六轮单要素串行迭代
cannot_do:
  - 直接写正文
  - 一次性生成全书400张施工卡
  - 让卷Agent改写全书大纲或设定集锁定项
```

---

# 第一部分：总流程

```text
立项通过
  -> 按 webnovel_outline_template_v1.md 生成全书宏观大纲
  -> 按 webnovel_setting_bible_template_v1.md 生成设定集
  -> 4个卷Agent分别生成每卷极简故事清单
  -> 章级施工卡Agent按需生成当前章施工卡
  -> 九步章节生产线第1步读取施工卡并生成输入卡
  -> 九步章节生产线第2-9步照旧执行
```

---

# 第二部分：Agent 编排

## 1. Chief Outline Orchestrator

```yaml
role: "大纲中台总调度"
responsibilities:
  - 校验立项包是否通过
  - 调用全书大纲模板
  - 调用设定集模板
  - 分派4个卷Agent
  - 汇总卷故事清单
  - 控制施工卡按需生成
  - 检查交接闸门
forbidden:
  - 不亲自写正文
  - 不跳过设定集
  - 不把整份大纲塞给单章生产线
```

## 2. Outline Agent

```yaml
role: "全书大纲Agent"
template: "webnovel_outline_template_v1.md"
output: "NovelMacroOutline"
must_include:
  - 商业定位
  - 一句话前提
  - 黄金三章
  - 四卷结构
  - 每卷目标、阻碍、代价、爆点
  - 爽点节奏与期待账本
forbidden:
  - 不写正文
  - 不生成章级施工卡
```

## 3. Setting Bible Agent

```yaml
role: "设定集Agent"
template: "webnovel_setting_bible_template_v1.md"
output: "NovelSettingBible"
must_include:
  - 世界宪法
  - 核心规则卡
  - 势力与机构
  - 人物连续性账本
  - 术语与认知负荷
  - 美学基座
  - 时间线与伏笔账本
forbidden:
  - 不覆盖大纲主线
  - 不无限扩写无冲突设定
```

## 4. 4个卷Agent

```yaml
agents:
  - volume_1_story_agent
  - volume_2_story_agent
  - volume_3_story_agent
  - volume_4_story_agent
input:
  - NovelMacroOutline
  - NovelSettingBible
output: "VolumeStoryList"
hard_rule: "4个卷Agent只能基于大纲和设定集设计每卷极简版故事清单。"
forbidden:
  - 不能改写全书大纲
  - 不能改写设定集锁定项
  - 不能生成正文
  - 不能直接进入九步第2步
```

## 5. Chapter Card Agent

```yaml
role: "章级施工卡Agent"
input:
  - NovelMacroOutline
  - NovelSettingBible
  - VolumeStoryList
  - previous_chapter_writeback
output: "ChapterConstructionCard"
generation_mode: "按需生成"
allowed_batch_scope:
  - single_chapter
  - unit
  - arc
  - volume
forbidden:
  - 不默认一次性生成400张施工卡
  - 不写正文
  - 不改变九步流程第2-9步
```

---

# 第三部分：人工闸门

```yaml
gates:
  outline_gate:
    required_before: "setting_bible"
    status: "通过 / 带风险通过 / 不通过"
  setting_bible_gate:
    required_before: "volume_story_list"
    status: "通过 / 带风险通过 / 不通过"
  volume_story_list_gate:
    required_before: "chapter_construction_card"
    status: "通过 / 带风险通过 / 不通过"
  handoff_gate:
    required_before: "nine_step_stage_1"
    status: "通过 / 带风险通过 / 不通过"
```

---

# 第四部分：失败与重试

```yaml
retry_policy:
  outline_failed:
    action: "回到立项包和大纲模板，重写全书结构，不进入设定集"
  setting_conflicts_outline:
    action: "设定集回滚到大纲约束内，不能改大纲主线"
  volume_agent_conflict:
    action: "总调度裁决，卷Agent只重写本卷故事清单"
  chapter_card_overloads_context:
    action: "删除非本章信息，只保留当前章施工卡和本章设定抽取包"
```

---

# 第五部分：版本记录

| 版本 | 日期 | 修改内容 | 修改原因 |
|---|---|---|---|
| v1.0 |  | 初版 | 补齐立项与九步章节生产线之间的大纲中台 |

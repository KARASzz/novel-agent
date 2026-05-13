# 🐉 红果剧本一键制造机 V3.0 (Industrial Edition)

**红果剧本一键制造机** 是一款为短剧创作者量身定制的工业级 RAG 生产管线。它通过深度集成阿里云百炼（Qwen-Max）大模型与 Tavily 实时雷达，将粗糙的创意草稿自动转化为高转化率、标准格式的短剧成品剧本，并辅以全方位的质量校验报告。

---

## 🌟 核心特性 (Core Features)

### 1. 🧠 混合动力 RAG 引擎 (Hybrid RAG)
- **双引擎自动降级**：优先调用阿里云百炼远程向量数据库，若遇网络波动自动无缝回退至本地 BM25 检索，确保生产永不断线。
- **响应式自动索引**：新知识（趋势、素材）入库后立即触发索引重建，知识库更新零延迟。

### 2. ⚡ 极限性能优化
- **Session Cache 策略**：全线适配 DashScope 最新 Responses API，自动启用 Session Cache，大幅降低长篇剧本处理的 Token 成本。
- **AIMD 速率控制**：内置加性增乘性减（AIMD）算法，根据 API 负载动态调节并发频率，彻底告别 429 限流报错。
- **多线程批处理**：支持横向扩展的剧本并行解析与验证，日产百集无压力。

### 3. 🛰️ 灵感探针与自动饲养 (Trend Intelligence)
- **实时趋势雷达**：集成 Tavily 深度搜索，一键刺探全网最新的“真假千金”、“赘婿打脸”等爆款变体。
- **全自动饲养员**：采集到的有效干货可自动清洗、提纯并同步至远程/本地知识库。

### 4. 🧪 工业级质量校验 (Validation)
- **神经科学校验逻辑**：针对黄金前三集、强力钩子（Cliffhangers）、冲突密度等 12 项关键指标进行自动化打分与诊断。

---

## 🚀 快速开始 (Quick Start)

项目已全面升级为标准 Python Package 结构及一键式控制台。

### 1. 环境准备
```bash
# 推荐使用 Python 3.11+
python -m pip install -e .
```

### 2. 启动控制台
直接双击运行项目根目录下的：
**`启动器.bat` (Industrial Console V3.0)**

你可以在菜单中一键执行：
- `[1]` 🚀 启动全自动流水线
- `[4]` 🛰️ 灵感探针 (获取最新套路)
- `[5]` 🌾 自动知识导入 (投喂 RAG)
- `[6]` 🧪 运行格式校验 (诊断剧本)

---

## 📂 项目结构 (Architecture)

```text
.
├── core_engine/          # 核心引擎 (Parser, Validator, Renderer, LLMClient)
├── rag_engine/           # RAG 模块 (Hybrid Retriever, Content Cleaner, Tavily)
├── scripts/              # 命令行工具与入口
├── drafts/               # [输入] 待处理的草稿文件夹
├── scripts_output/       # [输出] 渲染完成的成品剧本 (.txt)
├── reports/              # [输出] 详细的批处理质量报告 (.md)
├── knowledge_base/       # 本地 RAG 知识库存储
└── templates/            # 剧本输出模板与灵感卡片
```

---

## ⚙️ 配置说明 (Configuration)

编辑项目根目录的 `config.yaml`：

- `parser.model`: 建议使用 `qwen-max` 以获得最佳的钩子提取效果。
- `pipeline.max_workers`: 根据您的 API 额度调整并发数（推荐 3-10）。
- `rag.enable_hybrid`: 是否开启百炼远程+本地混合检索。

---

## 🛡️ 开发与维护

- **日志监控**：实时日志存储于 `logs/` 目录下，支持 JSON 结构化输出。
- **诊断项**：通过 `启动器.bat` 的选项 `[6]` 和 `[7]` 可快速定位渲染或逻辑异常。
- **缓存管理**：快照文件存储于 `.cache/`，可通过 CLI 关键词精准清理。

---
*愿每一部剧本都能成为千万级爆款。*

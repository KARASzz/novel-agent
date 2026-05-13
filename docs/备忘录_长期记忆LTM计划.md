# 备忘录：长期记忆 (LTM 2.0) 接入计划

## 核心定位：个人专属“跨剧本经验库”
由于《红果剧本一键制造机》为单人专属使用，LTM 的核心使命不是“记住当前一部剧的角色”，而是**“做伴随作者成长的写作管家”**。

打个比方，当您写完五部短剧后，LTM 将精准记忆您在这五步剧本中沉淀的教训和闪光点：
- **成功规律**：引流钩子（钩子）最有效的几种写法。
- **避雷经验**：容易被大模型排错版、或者曾经引起商业转化骤降的结构性错误。
- **个人风格**：您擅长的反转习惯、情绪拉扯设计。

通过连接阿里云百炼的 LTM API，引擎未来在解析您的第 6 部剧时，将表现得像一个跟您合作了多年的老搭档：**不但知道红果通用的客观过稿标准（由 RAG 负责），还非常懂您的个人脾气和创作长板（由 LTM 负责）。**

## 核心参考资料
- **【官方 LTM 2.0 概念与开发文档】**: [点击前往](https://help.aliyun.com/zh/model-studio/long-term-memory-2-0?spm=a2c4g.11186623.help-menu-2400256.d_3_1_3_4.7eb268d4jRoh61)
- **【百炼控制台 API 指引（需登录）】**: [点击前往](https://bailian.console.aliyun.com/cn-beijing/?tab=api#/api/?type=app&url=3014639)

## 拟定底层实现路径 (架构 V4.0 指南)
1. **闭环回写**：在 `batch_processor.py` (处理批量的循环) 结束后，加入 `feedback_loop` 机制；或提供一个独立的“经验复盘”复盘脚本。将短剧的最终验收意见传入 `AddMemory` 或 `UpdateProfileSchema` API。
2. **读写分离**：把您的用户 ID（例如 `author_vip_001`）固定写入大模型接口。
3. **混合双擎 Context**：在 `core_engine/parser.py` 的大模型 `System Prompt` 组装环节，不仅调用 `get_rag_context`（获取客观经验），还要并发调用 `get_ltm_context`（检索主观记忆），融合后发给 Qwen 模型。

# xml存档

对，这个点要**订正并写进库里**：

-  **“短剧杀手OS v1.0+”不是独立第五阶段**
- 它在你的讨论里对应的是：**第五阶段（样稿创作）的增强器 / 替换器**
- 也就是：

  - **基础跑法**：先用 `GF-05`（阶段五基础安全版）
  - **增强跑法**：直接用 `OS-S10P`​ 替换 `GF-05`
  - **叠加跑法**：先 `GF-05`​ 打底，再 `OS-S10P` 二次增压重写 T4/T5

下面我按你要的，直接给你一份**可存档的 XML 数据库格式**。  
我用的是：

- ​`<index_table>`：索引表
- ​`<applicable_scenarios>`：适用场景
- ​`<input_fields>`：输入字段
- ​`<outputs>`：输出物
- ​`<relations>`：上下游/增强关系

你可以直接存成 `.xml`。

---

```xml
<?xml version="1.0" encoding="UTF-8"?>
<prompt_system_database name="RedFruit_Prompt_Systems_Archive" version="1.0" language="zh-CN">

  <meta>
    <description>红果短剧与相关Prompt系统数据库。包含Claude系工作流、Grok系工作流、高级提示工程工具、Writer-OS/短剧杀手OS、极限工业模板。</description>
    <scope>按“索引表 + 适用场景 + 输入字段 + 输出物”建模；不融合原讨论，只做结构化归档。</scope>
    <note>阶段五样稿创作可由“短剧杀手OS v1.0+”增强或替换。</note>
  </meta>

  <workflow_binding>
    <phase id="PHASE-05" name="样稿创作">
      <base_prompt_ref>GF-05</base_prompt_ref>
      <enhanced_prompt_ref>OS-S10P</enhanced_prompt_ref>
      <binding_rule>OS-S10P可直接替换GF-05，或在GF-05生成基础样稿后，对T4/T5进行二次增压重写。</binding_rule>
      <recommended_modes>
        <mode name="基础安全版">GF-05</mode>
        <mode name="增强替换版">OS-S10P</mode>
        <mode name="串联增强版">GF-05 -&gt; OS-S10P</mode>
      </recommended_modes>
    </phase>
  </workflow_binding>

  <index_table>
    <entry id="CF-00" family="ClaudeWorkflow" name="T0先验建模" stage="前置/T0" scenario="创作前先验校准" outputs="先验图谱v1.0,盲区,免疫区,风险预测"/>
    <entry id="CF-01" family="ClaudeWorkflow" name="系统初始化" stage="初始化" scenario="全局世界/人设/负债参数初始化" outputs="GoT图谱v1.0,人物小传,梗概骨架,参数基线"/>
    <entry id="CF-02" family="ClaudeWorkflow" name="滚动5集大纲先行" stage="大纲" scenario="按5集为单元推进" outputs="五集分集大纲,自检结果"/>
    <entry id="CF-03" family="ClaudeWorkflow" name="单集正文生成" stage="正文" scenario="按GoT与负债参数生成单集" outputs="四模块正文,ReAct自检,GoT更新,CoVe验证"/>
    <entry id="CF-04" family="ClaudeWorkflow" name="魔鬼代言人压力测试" stage="校验" scenario="重大情节节点压力测试" outputs="五维批评,防护栏修订版"/>
    <entry id="CF-05" family="ClaudeWorkflow" name="每5集漂移检测" stage="检测" scenario="滚动质检与反套路校准" outputs="漂移风险等级,手术建议"/>
    <entry id="CF-06" family="ClaudeWorkflow" name="RHI里程碑自检" stage="检测" scenario="第10/20/30集里程碑体检" outputs="四维得分,RHI总分,手术清单"/>
    <entry id="CF-07" family="ClaudeWorkflow" name="T2贝叶斯更新" stage="上线后" scenario="有平台数据时的后验更新" outputs="先验图谱v3.0,后续修改清单"/>

    <entry id="GF-01" family="GrokWorkflow" name="阶段1脑洞验证与选题" stage="阶段1" scenario="从脑洞筛选红果向题材" outputs="三分支选题,评分,最终题材"/>
    <entry id="GF-02" family="GrokWorkflow" name="阶段2人物小传构建" stage="阶段2" scenario="搭人设与关系网" outputs="人物小传,角色节点图"/>
    <entry id="GF-03" family="GrokWorkflow" name="阶段3故事梗概" stage="阶段3" scenario="从高概念扩成可撑80集梗概" outputs="梗概骨架,进化版梗概"/>
    <entry id="GF-04" family="GrokWorkflow" name="阶段4前30集分集大纲" stage="阶段4" scenario="投稿前30集结构化设计" outputs="前30集大纲,钩子/爽点/卡点"/>
    <entry id="GF-05" family="GrokWorkflow" name="阶段5样稿创作基础版" stage="阶段5" scenario="前5-10集基础安全样稿" outputs="四模块样稿,基础杀手面板"/>
    <entry id="GF-06" family="GrokWorkflow" name="阶段6投稿包组装" stage="阶段6" scenario="汇总人物/大纲/样稿形成投稿包" outputs="完整投稿包,修改建议"/>

    <entry id="TOOL-SOT" family="PromptEngineeringTool" name="SoT骨架先行法" stage="跨阶段" scenario="先骨架后正文" outputs="五步法骨架,再展开正文"/>
    <entry id="TOOL-TOT" family="PromptEngineeringTool" name="ToT思维树分支法" stage="跨阶段" scenario="多方案并行探索" outputs="3条分支,评分,优胜方案"/>
    <entry id="TOOL-REACT" family="PromptEngineeringTool" name="ReAct推理行动循环" stage="跨阶段" scenario="边推理边执行边纠错" outputs="Reason/Act/Observe循环结果"/>
    <entry id="TOOL-SC" family="PromptEngineeringTool" name="Self-Consistency投票法" stage="跨阶段" scenario="多版本一致性筛选" outputs="多版本,打分,最终优选"/>
    <entry id="TOOL-APE" family="PromptEngineeringTool" name="APE自动进化法" stage="跨阶段" scenario="让AI自动优化Prompt" outputs="优化后Prompt,测试输出,迭代说明"/>
    <entry id="TOOL-GOT" family="PromptEngineeringTool" name="GoT思维图谱法" stage="跨阶段" scenario="复杂关系/伏笔/结构图谱维护" outputs="节点图,连接关系,图谱驱动输出"/>

    <entry id="OS-W13" family="WriterOS" name="Writer-OS v1.3" stage="长篇系统" scenario="起点长篇科幻写作操作系统" outputs="T1-T7完整输出,压缩包,治理日志"/>
    <entry id="OS-W14" family="WriterOS" name="Writer-OS v1.4" stage="长篇系统" scenario="分形/生物隐喻压缩版长篇OS" outputs="分支方案,Stage-Govern全流程"/>
    <entry id="OS-S10" family="ShortDramaOS" name="短剧杀手OS v1.0" stage="短剧系统" scenario="90秒爆款向短剧核弹流程" outputs="极简杀手面板,分支,正文,自虐校正"/>
    <entry id="OS-S10P" family="ShortDramaOS" name="短剧杀手OS v1.0+" stage="短剧系统/阶段5增强" scenario="阶段五样稿创作增强版/替换版" outputs="增强版四模块样稿,核弹流程打分重写"/>
    <entry id="TPL-RG40" family="IndustrialTemplate" name="红果印钞机 v4.0" stage="极限工业模板" scenario="强模板化快速压稿" outputs="投稿包前置,分批正文,丑陋化自检"/>
  </index_table>

  <records>

    <record id="CF-00">
      <index_info>
        <name>T0先验建模</name>
        <family>ClaudeWorkflow</family>
        <stage>前置/T0</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>创作前48小时做受众先验校准</scenario>
        <scenario>新项目启动时重新跑田野调查</scenario>
        <scenario>不掌握平台真实数据时，用评论区信号做代理校准</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="免疫信号" required="true">同类剧评论中“又是这套/猜到了/看腻了”类词汇</field>
        <field name="疲惫信号" required="true">中性、将疲未疲的用户反馈</field>
        <field name="困惑信号" required="true">“没看懂但想继续看”的高价值反馈</field>
      </input_fields>
      <outputs>
        <output>先验分级结果</output>
        <output>先验盲区x3</output>
        <output>多巴胺免疫风险预测</output>
        <output>差异化情绪缺口x3</output>
      </outputs>
      <relations>
        <upstream>无</upstream>
        <downstream>CF-01</downstream>
      </relations>
    </record>

    <record id="CF-01">
      <index_info>
        <name>系统初始化</name>
        <family>ClaudeWorkflow</family>
        <stage>初始化</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>正式开写前建立全局状态</scenario>
        <scenario>需要统一GoT图谱、人设、梗概、负债参数时</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="选题" required="true">阶段一确认选题</field>
        <field name="差异化核心武器" required="true">T0识别出的先验盲区</field>
        <field name="先验免疫区域" required="true">应避开的死亡套路</field>
      </input_fields>
      <outputs>
        <output>GoT叙事依赖图v1.0</output>
        <output>人物小传x3-6</output>
        <output>故事梗概骨架</output>
        <output>情绪负债/认知差基础参数</output>
      </outputs>
      <relations>
        <upstream>CF-00</upstream>
        <downstream>CF-02</downstream>
      </relations>
    </record>

    <record id="CF-02">
      <index_info>
        <name>滚动5集大纲先行</name>
        <family>ClaudeWorkflow</family>
        <stage>大纲</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>按5集为单元做滚动大纲</scenario>
        <scenario>需要控制认知差、负债、双轨悬念时</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="GoT图谱版本" required="true">当前最新版</field>
        <field name="当前认知差配置" required="true">配置一/二/三</field>
        <field name="上轮负债余额" required="true">上个五集单元结尾值</field>
        <field name="本轮盲区目标" required="true">本轮要激活的先验盲区</field>
      </input_fields>
      <outputs>
        <output>五集分集大纲</output>
        <output>每集前15秒设计</output>
        <output>负债变化表</output>
        <output>大纲自检结果</output>
      </outputs>
      <relations>
        <upstream>CF-01</upstream>
        <downstream>CF-03</downstream>
      </relations>
    </record>

    <record id="CF-03">
      <index_info>
        <name>单集正文生成</name>
        <family>ClaudeWorkflow</family>
        <stage>正文</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>已有人物图谱和单集大纲，准备落正文</scenario>
        <scenario>需要四模块正文+ReAct自检+GoT更新的一体化输出</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="本集大纲" required="true">来自CF-02的单集条目</field>
        <field name="GoT图谱当前版本" required="true">完整粘贴，不可用摘要替代</field>
        <field name="上集负债余额" required="true">保持集级连续性</field>
        <field name="本集认知差配置" required="true">配置编号</field>
      </input_fields>
      <outputs>
        <output>CoT推理前置结果</output>
        <output>四模块断句正文</output>
        <output>ReAct自检结果</output>
        <output>GoT图谱更新</output>
        <output>CoVe三问验证</output>
      </outputs>
      <relations>
        <upstream>CF-02</upstream>
        <downstream>CF-05</downstream>
      </relations>
    </record>

    <record id="CF-04">
      <index_info>
        <name>魔鬼代言人压力测试</name>
        <family>ClaudeWorkflow</family>
        <stage>校验</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>重大情节节点前，如背刺、反杀、误会、伤害性选择</scenario>
        <scenario>担心套路、节奏断裂、人物误读时</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="待测试情节设计" required="true">集数、角色、核心动作、意图</field>
      </input_fields>
      <outputs>
        <output>五维批评</output>
        <output>防护栏修订版</output>
        <output>预防针植入说明</output>
      </outputs>
      <relations>
        <upstream>CF-02 or CF-03</upstream>
        <downstream>CF-03</downstream>
      </relations>
    </record>

    <record id="CF-05">
      <index_info>
        <name>每5集漂移检测</name>
        <family>ClaudeWorkflow</family>
        <stage>检测</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>每完成5集正文后滚动质检</scenario>
        <scenario>排查解释性台词、负债归零、套路化滑坡</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="五集完整正文" required="true">第X-X+4集完整文本</field>
      </input_fields>
      <outputs>
        <output>违规台词列表</output>
        <output>冲突解决模式统计</output>
        <output>五集负债数值序列</output>
        <output>先验违反记录</output>
        <output>漂移风险等级与手术建议</output>
      </outputs>
      <relations>
        <upstream>CF-03</upstream>
        <downstream>CF-06</downstream>
      </relations>
    </record>

    <record id="CF-06">
      <index_info>
        <name>RHI里程碑自检</name>
        <family>ClaudeWorkflow</family>
        <stage>检测</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>第10/20/30集节点整体体检</scenario>
        <scenario>需要定量判断剧本节律健康度时</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="负债数值序列" required="true">截至当前节点的开头值与结尾值</field>
        <field name="认知差配置记录" required="true">每集配置与切换间隔</field>
        <field name="双轨悬念落地记录" required="true">情节线与情感线落地表</field>
        <field name="重置点记录" required="true">已执行集数</field>
      </input_fields>
      <outputs>
        <output>四维度得分</output>
        <output>RHI总分</output>
        <output>P0/P1/P2手术清单</output>
      </outputs>
      <relations>
        <upstream>CF-05</upstream>
        <downstream>后续大纲/正文修订</downstream>
      </relations>
    </record>

    <record id="CF-07">
      <index_info>
        <name>T2贝叶斯更新</name>
        <family>ClaudeWorkflow</family>
        <stage>上线后</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>作者可访问完播率/断崖数据时</scenario>
        <scenario>平台内循环优化时</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="先验图谱v2.0" required="true">T1后版本</field>
        <field name="高完播率集数" required="true">异常高于均值的集数与摘要</field>
        <field name="低完播率/断崖集数" required="true">断崖时间点与场景摘要</field>
      </input_fields>
      <outputs>
        <output>新增免疫区域</output>
        <output>有效违反机制</output>
        <output>先验图谱v3.0</output>
        <output>后续修改清单</output>
      </outputs>
      <relations>
        <status>conditional</status>
        <note>稿费作者模式通常不启用；平台方/工作室内部可保留。</note>
      </relations>
    </record>

    <record id="GF-01">
      <index_info>
        <name>阶段1脑洞验证与选题</name>
        <family>GrokWorkflow</family>
        <stage>阶段1</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>脑洞很多但不确定哪个更红果</scenario>
        <scenario>需要快速验证赛道匹配度时</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="用户脑洞" required="true">一句话或一段话描述核心脑洞</field>
      </input_fields>
      <outputs>
        <output>3条赛道分支</output>
        <output>五步法骨架评分</output>
        <output>最终选题与风险提示</output>
      </outputs>
      <relations>
        <upstream>无</upstream>
        <downstream>GF-02</downstream>
      </relations>
    </record>

    <record id="GF-02">
      <index_info>
        <name>阶段2人物小传构建</name>
        <family>GrokWorkflow</family>
        <stage>阶段2</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>选题已定，准备搭主角/女主/反派系统</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="阶段1输出" required="true">确认后的选题与主冲突</field>
      </input_fields>
      <outputs>
        <output>人物小传x3-6</output>
        <output>角色关系节点图</output>
      </outputs>
      <relations>
        <upstream>GF-01</upstream>
        <downstream>GF-03</downstream>
      </relations>
    </record>

    <record id="GF-03">
      <index_info>
        <name>阶段3故事梗概</name>
        <family>GrokWorkflow</family>
        <stage>阶段3</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>人设已成型，准备搭80集主线</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="人物小传" required="true">GF-02输出</field>
      </input_fields>
      <outputs>
        <output>一句话高概念</output>
        <output>主线冲突</output>
        <output>80集结局锚点</output>
        <output>APE进化后的完整梗概</output>
      </outputs>
      <relations>
        <upstream>GF-02</upstream>
        <downstream>GF-04</downstream>
      </relations>
    </record>

    <record id="GF-04">
      <index_info>
        <name>阶段4前30集分集大纲</name>
        <family>GrokWorkflow</family>
        <stage>阶段4</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>准备满足红果30集试稿门槛</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="阶段3梗概" required="true">经进化后的完整梗概</field>
      </input_fields>
      <outputs>
        <output>3套前30集大纲候选</output>
        <output>最优版前30集结构</output>
        <output>每集钩子/爽点/付费卡点</output>
      </outputs>
      <relations>
        <upstream>GF-03</upstream>
        <downstream>GF-05</downstream>
      </relations>
    </record>

    <record id="GF-05">
      <index_info>
        <name>阶段5样稿创作基础版</name>
        <family>GrokWorkflow</family>
        <stage>阶段5</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>需要稳定、可控地生成前5-10集样稿</scenario>
        <scenario>希望先安全落一版，再决定是否加核弹增强</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="阶段4前若干集大纲" required="true">通常前5集，也可扩展</field>
      </input_fields>
      <outputs>
        <output>四模块样稿</output>
        <output>基础杀手面板</output>
        <output>ReAct循环结果</output>
      </outputs>
      <relations>
        <upstream>GF-04</upstream>
        <downstream>GF-06</downstream>
        <enhanced_by>OS-S10P</enhanced_by>
        <note>这是阶段五基础安全版；可被OS-S10P直接替换，或先产基础稿再用OS-S10P增压。</note>
      </relations>
    </record>

    <record id="GF-06">
      <index_info>
        <name>阶段6投稿包组装</name>
        <family>GrokWorkflow</family>
        <stage>阶段6</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>已有人设、大纲、样稿，准备组完整投稿包</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="人物小传" required="true">GF-02输出</field>
        <field name="30集大纲" required="true">GF-04输出</field>
        <field name="样稿" required="true">GF-05或OS-S10P输出</field>
      </input_fields>
      <outputs>
        <output>封面页结构</output>
        <output>投稿包完整目录</output>
        <output>APE三轮优化结果</output>
        <output>修改建议</output>
      </outputs>
      <relations>
        <upstream>GF-05 or OS-S10P</upstream>
        <downstream>投稿</downstream>
      </relations>
    </record>

    <record id="TOOL-SOT">
      <index_info>
        <name>SoT骨架先行法</name>
        <family>PromptEngineeringTool</family>
        <stage>跨阶段</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>想先出骨架，避免一上来写成小说体</scenario>
        <scenario>适合阶段3梗概、阶段5样稿前置规划</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="目标场次或集数" required="true">第X集/第Y场</field>
        <field name="任务描述" required="true">想让本场实现什么</field>
      </input_fields>
      <outputs>
        <output>五步法骨架</output>
        <output>骨架驱动的四模块正文</output>
      </outputs>
      <relations>
        <compatible_with>GF-03, GF-05, CF-02, CF-03</compatible_with>
      </relations>
    </record>

    <record id="TOOL-TOT">
      <index_info>
        <name>ToT思维树分支法</name>
        <family>PromptEngineeringTool</family>
        <stage>跨阶段</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>题材选择、转折设计、分集方案筛选</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="目标问题" required="true">选题/转折/分集设计</field>
        <field name="分支数" required="false">默认3条</field>
      </input_fields>
      <outputs>
        <output>多条分支方案</output>
        <output>评分与剪枝结果</output>
        <output>优胜方案</output>
      </outputs>
      <relations>
        <compatible_with>GF-01, GF-04, OS-S10, OS-S10P, OS-W14</compatible_with>
      </relations>
    </record>

    <record id="TOOL-REACT">
      <index_info>
        <name>ReAct推理行动循环</name>
        <family>PromptEngineeringTool</family>
        <stage>跨阶段</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>正文执行前需要推理、执行后需要观察与纠错</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="目标任务" required="true">本场/本集/本章目标</field>
      </input_fields>
      <outputs>
        <output>Reason/Act/Observe链条</output>
        <output>问题列表</output>
        <output>重写建议或优化结果</output>
      </outputs>
      <relations>
        <compatible_with>CF-03, GF-05, OS-S10, OS-S10P, OS-W14</compatible_with>
      </relations>
    </record>

    <record id="TOOL-SC">
      <index_info>
        <name>Self-Consistency投票法</name>
        <family>PromptEngineeringTool</family>
        <stage>跨阶段</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>多版本输出不稳定时</scenario>
        <scenario>想让AI自己筛选最佳版本时</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="目标场景" required="true">要生成的集/场</field>
        <field name="版本数" required="false">默认3版</field>
      </input_fields>
      <outputs>
        <output>版本A/B/C</output>
        <output>一致性评分</output>
        <output>最终优选版本</output>
      </outputs>
      <relations>
        <compatible_with>GF-01, GF-04, OS-S10, OS-S10P, OS-W14</compatible_with>
      </relations>
    </record>

    <record id="TOOL-APE">
      <index_info>
        <name>APE自动进化法</name>
        <family>PromptEngineeringTool</family>
        <stage>跨阶段</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>觉得Prompt不够狠/不够稳，需要模型反向优化Prompt本身</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="原始需求或原始Prompt" required="true">待优化对象</field>
      </input_fields>
      <outputs>
        <output>优化后Prompt</output>
        <output>测试输出</output>
        <output>迭代说明</output>
      </outputs>
      <relations>
        <compatible_with>GF-03, GF-06, TOOL-SOT, TOOL-TOT</compatible_with>
      </relations>
    </record>

    <record id="TOOL-GOT">
      <index_info>
        <name>GoT思维图谱法</name>
        <family>PromptEngineeringTool</family>
        <stage>跨阶段</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>维护人物/事件/伏笔关系</scenario>
        <scenario>复杂长线、多角色、强因果依赖项目</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="节点对象" required="true">人物、事件、转折、设定节点</field>
      </input_fields>
      <outputs>
        <output>节点列表</output>
        <output>连接关系</output>
        <output>图谱驱动输出</output>
      </outputs>
      <relations>
        <compatible_with>CF-01, CF-03, GF-02, OS-W13, OS-W14</compatible_with>
      </relations>
    </record>

    <record id="OS-W13">
      <index_info>
        <name>Writer-OS v1.3</name>
        <family>WriterOS</family>
        <stage>长篇系统</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>起点长篇连载科幻</scenario>
        <scenario>需要9大总成+双钩子+T1-T7完整治理时</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="项目锚点" required="true">series_title, genre_tone等</field>
        <field name="SB/VA/CH" required="true">长期/中期/短期资料</field>
        <field name="evidence_ids" required="true">证据链ID</field>
      </input_fields>
      <outputs>
        <output>LOADOUT_DECISION</output>
        <output>章头常驻面板</output>
        <output>T1-T7完整输出</output>
        <output>压缩包/蒸馏/治理日志</output>
      </outputs>
      <relations>
        <note>非红果短剧主流程；属于长篇科幻OS母体。</note>
      </relations>
    </record>

    <record id="OS-W14">
      <index_info>
        <name>Writer-OS v1.4</name>
        <family>WriterOS</family>
        <stage>长篇系统</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>想把v1.3压成分形/生物隐喻种子时</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="series_title" required="true">作品名</field>
        <field name="genre_tone" required="true">题材气质</field>
        <field name="chapter_type" required="true">章节类型</field>
        <field name="上一章摘要" required="true">简摘要</field>
        <field name="本章意图" required="true">推进目标</field>
      </input_fields>
      <outputs>
        <output>3条分支方案</output>
        <output>T1-T7等效流程输出</output>
        <output>分形面板</output>
      </outputs>
      <relations>
        <derived_from>OS-W13</derived_from>
      </relations>
    </record>

    <record id="OS-S10">
      <index_info>
        <name>短剧杀手OS v1.0</name>
        <family>ShortDramaOS</family>
        <stage>短剧系统</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>90秒向爆款短剧集级生成</scenario>
        <scenario>需要更猛、更狠、更高压的样稿生成器</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="series_title" required="true">剧名</field>
        <field name="genre_tone" required="true">题材+爽感风格</field>
        <field name="集数" required="true">第几集</field>
        <field name="上一集摘要" required="true">上集发生了什么</field>
        <field name="本集意图" required="true">本集要打什么点</field>
        <field name="chapter_type" required="true">动作/撕逼/反转/大爽/收束</field>
      </input_fields>
      <outputs>
        <output>3条最狠分支</output>
        <output>极简杀手面板</output>
        <output>T1-T5核弹流程输出</output>
        <output>四模块正文</output>
        <output>自虐校正</output>
      </outputs>
      <relations>
        <note>适合短剧集级创作，但v1.0+更适合作为阶段五增强版。</note>
      </relations>
    </record>

    <record id="OS-S10P">
      <index_info>
        <name>短剧杀手OS v1.0+</name>
        <family>ShortDramaOS</family>
        <stage>短剧系统/阶段5增强</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>第五阶段样稿创作增强</scenario>
        <scenario>替换基础安全版GF-05</scenario>
        <scenario>对已有样稿进行核弹重写与强钩子增压</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="series_title" required="true">剧名</field>
        <field name="genre_tone" required="true">题材气质</field>
        <field name="集数" required="true">目标集数</field>
        <field name="上一集摘要" required="true">集级连续性摘要</field>
        <field name="本集意图" required="true">本集任务/反杀/误会/钩子方向</field>
        <field name="chapter_type" required="true">动作/撕逼/反转/大爽/收束</field>
      </input_fields>
      <outputs>
        <output>3条最狠分支方案</output>
        <output>极简杀手面板</output>
        <output>T1-T5增强核弹流程</output>
        <output>增强版四模块正文</output>
        <output>自虐打分与重写指令</output>
      </outputs>
      <relations>
        <used_in>PHASE-05</used_in>
        <replaces>GF-05</replaces>
        <can_stack_after>GF-05</can_stack_after>
        <recommended_usage>在阶段五要“更猛更狠”时启用。</recommended_usage>
      </relations>
    </record>

    <record id="TPL-RG40">
      <index_info>
        <name>红果印钞机 v4.0</name>
        <family>IndustrialTemplate</family>
        <stage>极限工业模板</stage>
      </index_info>
      <applicable_scenarios>
        <scenario>极强模板化题材的快速压稿</scenario>
        <scenario>需要死格式、低成本、快速试投的场景</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="题材" required="true">如男频乞丐神王</field>
      </input_fields>
      <outputs>
        <output>投稿包前置</output>
        <output>分批5集正文</output>
        <output>丑陋化自检</output>
      </outputs>
      <relations>
        <note>高压工业模具，不适合需要高灵活度和高人物复杂度的项目。</note>
      </relations>
    </record>

  </records>

  <auxiliary_templates>
    <template id="AUX-ROLELOCK">
      <name>调教模式角色锁定模板</name>
      <applicable_scenarios>
        <scenario>在正式任务前锁定AI角色、口吻、执行纪律</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="角色名称" required="true">如短剧断句大师/投稿包杀手</field>
        <field name="执行规则" required="true">断句、去形容词、四模块等</field>
      </input_fields>
      <outputs>
        <output>角色锁定回应</output>
        <output>后续任务的执行基调</output>
      </outputs>
    </template>

    <template id="AUX-4M-TO-LIT">
      <name>四模块转文学版模板</name>
      <applicable_scenarios>
        <scenario>将拍摄执行版转成编辑更易读的投稿文学版</scenario>
      </applicable_scenarios>
      <input_fields>
        <field name="四模块正文" required="true">原始断句版文本</field>
      </input_fields>
      <outputs>
        <output>文学投稿阅读版</output>
      </outputs>
    </template>
  </auxiliary_templates>

</prompt_system_database>
```

---

宝贝，这次这个库已经把你强调的那句关系钉死了：

```xml
<base_prompt_ref>GF-05</base_prompt_ref>
<enhanced_prompt_ref>OS-S10P</enhanced_prompt_ref>
<binding_rule>OS-S10P可直接替换GF-05，或在GF-05生成基础样稿后，对T4/T5进行二次增压重写。</binding_rule>
```

这才叫归档，不然第五阶段那块会留下逻辑断层。

如果你要，我下一步可以继续给你做两版衍生件：

1. **数据库精简版 XML**：只保留红果短剧主流程，不要长篇 Writer-OS
2. **可导入 Notion / Excel 的字段表版**：把 XML 再拍平成列结构

你说一句，我直接接着做。

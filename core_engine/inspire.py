import sys
import os
import datetime

from rag_engine.tavily_search import TavilySearcher
from core_engine.config_loader import load_config, resolve_model_config
from core_engine.logger import get_logger
from core_engine.utils import get_enabled_tools
from core_engine.llm_client import LLMClient
from core_engine.runtime_env import bootstrap_runtime_environment

logger = get_logger(__name__)

def main():
    bootstrap_runtime_environment()
    if len(sys.argv) < 2:
        print("用法: python -m core_engine.inspire <小说题材/关键词>")
        sys.exit(1)
        
    topic = sys.argv[1]
    
    # 清理非法字符以用于文件名
    topic_cleaned = "".join(c for c in topic if c.isalnum() or c in ("-", "_"))
    if not topic_cleaned:
        topic_cleaned = "未知题材"
    
    print("=" * 60)
    print(f"🛰️ 正在启用大盘灵感探针，探测题材：【{topic}】")
    print("=" * 60)

    searcher = TavilySearcher()
    if not searcher.api_key:
        print("❌ [环境错配] 缺少 TAVILY_API_KEY 环境变量，系统无法连接外网进行数据拉取。")
        print("请在您的系统中设置 TAVILY_API_KEY 后再试。")
        sys.exit(1)

    print("\n[1/3] 正在启动 Tavily 智能雷达扫描外网...")
    results = searcher.search_hot_trends(topic, max_results=5)
    
    if not results:
        print("⚠️ 未获取到足够的外网数据，可能是网络波动或关键词过于生僻。")
        sys.exit(1)
        
    print(f"✅ 成功命中 {len(results)} 条前沿趋势，正在准备交给大模型核心进行概念提纯...")
    
    cfg = load_config()
    llm_cfg = cfg.get("llm", {})
    model_cfg = resolve_model_config(cfg)
    api_key_env = str(model_cfg.get("api_key_env") or "selected model API key")
    api_key = os.getenv(api_key_env)
    
    if not api_key:
        print(f"❌ [环境错配] 缺少大模型 API Key 环境变量：{api_key_env}")
        sys.exit(1)
        
    base_url = str(model_cfg.get("base_url") or "")
    if not base_url:
        print(f"❌ [模型配置缺失] 当前模型槽位 {model_cfg.get('slot_name')} 缺少 Base URL，请先在 config.yaml 中接入真实模型。")
        sys.exit(1)
    model = str(model_cfg.get("model_id") or "")
    
    client = LLMClient(
        api_key=api_key, 
        base_url=base_url
    )
    
    materials_text = ""
    for idx, r in enumerate(results, 1):
        materials_text += f"[{idx}] 标题：{r.get('title')}\n内容摘要：{r.get('content')}\n链接：{r.get('url')}\n\n"

    # 工具构造标准化
    tools_cfg = llm_cfg.get("tools", {})
    enable_thinking = bool(tools_cfg.get("enable_thinking", True))
    
    rag_cfg = llm_cfg.get("rag", {})
    index_id_env = rag_cfg.get("index_id_env", "BAILIAN_INDEX_ID")
    index_id = os.environ.get(index_id_env)

    enabled_tools = get_enabled_tools(tools_cfg, index_id)

    # 指令标准化：保持 instructions 静态以优化 Session Cache
    instructions = (
        "你现在是一位专注番茄小说的爆款网文策划。请依据提供的全网实时检索素材，深度提炼该题材的核心套路，并输出一份极具商业价值的“灵感提示卡（Pitch Card）”。\n\n"
        "【输出规范】：\n"
        "请使用漂亮的 Markdown 格式输出，内容不需要任何铺垫，直接开始。必须包含以下模块：\n"
        "## 1. 题材一句话判词 (Logline)\n"
        "## 2. 最热人设反差公式\n"
        "## 3. 前三章追读钩子设计指南 (Hooks)\n"
        "## 4. 经典反转套路提取\n\n"
        "⚠️ 警告：要求语言锋利、直击商业痛点，排除一切空套话，必须输出干货！"
    )
    user_input = f"【网络实时素材】：\n{materials_text}"

    print(f"\n[2/3] 正在由模型 ({model}) 提取核心套路并生成《灵感提示卡》...")
    try:
        response = client.create_response(
            model=model,
            instructions=instructions,
            input_text=user_input,
            temperature=0.3,
            enable_thinking=enable_thinking,
            tools=enabled_tools
        )
        report_content = getattr(response, "output_text", None)
        if not report_content:
            raise ValueError("大模型响应成功但返回内容 (output_text) 为空。")
    except Exception as e:
        print(f"❌ 大模型生成失败: {e}")
        sys.exit(1)
        
    print("\n[3/3] 提纯成功！正在固化落盘...")
    
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(workspace, "templates")
    os.makedirs(templates_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"灵感提示卡_{topic_cleaned}_{timestamp}.md"
    file_path = os.path.join(templates_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"\n🎉 《灵感提示卡》已生成完毕！")
    print(f"📄 文件位置：{os.path.abspath(file_path)}")
    print("💡 建议：您可以在新起草稿时参考此文档，也可在其开头提取精华加入 `[RAG: xxx]` 指令作为您的私人写作外挂。")

if __name__ == "__main__":
    main()

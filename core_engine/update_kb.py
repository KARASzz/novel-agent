import sys
import os
import re
import datetime

from rag_engine.tavily_search import TavilySearcher
from core_engine.config_loader import load_config, resolve_model_config
from core_engine.logger import get_logger
from core_engine.llm_client import LLMClient

logger = get_logger(__name__)

def main():
    if len(sys.argv) < 2:
        print("用法: python -m core_engine.update_kb <需要补充的知识库主题>")
        sys.exit(1)
        
    topic = sys.argv[1]
    
    print("=" * 60)
    print(f"🤖 [本地知识库饲养员] 正在收集番茄小说参考资料：【{topic}】")
    print("=" * 60)
    
    searcher = TavilySearcher()
    if not searcher.api_key:
        print("错误：未配置 TAVILY_API_KEY 环境变量。")
        sys.exit(1)
        
    print("\n[1/4] 启动 Tavily 雷达收集材料...")
    results = searcher.search_hot_trends(topic, max_results=5)
    if not results:
        print("网络雷达未收集到有效素材。")
        sys.exit(1)
        
    cfg = load_config()
    llm_cfg = cfg.get("llm", {})
    model_cfg = resolve_model_config(cfg)
    api_key_env = str(model_cfg.get("api_key_env") or "selected model API key")
    api_key = os.getenv(api_key_env)
    
    if not api_key:
        print(f"错误：缺少环境变量：{api_key_env}")
        sys.exit(1)
        
    print("\n[2/3] 交由所选模型梳理干货并撰写 Markdown 报告...")
    base_url = str(model_cfg.get("base_url") or "")
    if not base_url:
        print(f"错误：当前模型槽位 {model_cfg.get('slot_name')} 缺少 Base URL，请先在 config.yaml 中接入真实模型。")
        sys.exit(1)
    model = str(model_cfg.get("model_id") or "")
    client = LLMClient(
        api_key=api_key, 
        base_url=base_url
    )
    
    materials_text = ""
    for idx, r in enumerate(results, 1):
        materials_text += f"[{idx}] {r.get('title')}\n{r.get('content')}\n\n"
        
    # 指令标准化：定义研究员角色与标准规范（保持静态以优化 Session Cache）
    instructions = (
        "你是一个专业的番茄小说网文研究员。请针对用户提供的情报素材，整理出一篇结构清晰、极具实战价值的 Markdown 归纳文章。\n"
        "要求：\n1. 核心定义提取。\n2. 经典爽点与套路总结。\n3. 实战编写建议。\n4. 必须写明 3 个该题材的负面避坑指南。\n"
        "5. 必须输出纯粹的 Markdown 文档，不含多余的寒暄问候。"
    )
    user_input = f"【研究主题】：{topic}\n\n【收集到的热门情报材料】：\n{materials_text}"

    try:
        response = client.create_response(
            model=model,
            instructions=instructions,
            input_text=user_input,
            temperature=0.4,
            enable_thinking=bool(llm_cfg.get("tools", {}).get("enable_thinking", True)),
        )
        report_content = getattr(response, "output_text", None)
        if not report_content:
            raise ValueError("大模型返回的内容为空 (output_text 为空)")
    except Exception as e:
        print(f"模型生成失败: {e}")
        sys.exit(1)
        
    # 保存文件
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kb_dir = os.path.join(workspace, "knowledge_base")
    os.makedirs(kb_dir, exist_ok=True)
    
    # 文件名安全清洗
    topic_cleaned = re.sub(r'[^\w\u4e00-\u9fa5\-]', '_', topic).strip('_')
    if not topic_cleaned:
        topic_cleaned = "unknown_subject"
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"KB_{topic_cleaned}_{timestamp}.md"
    file_path = os.path.join(kb_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"\n[3/3] 高质量资料报告已在本地生成：{file_path}")
    print("百炼向量库模块已冻结：本命令只更新本地知识库，不上传云端。")

if __name__ == "__main__":
    main()

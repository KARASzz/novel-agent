import sys
import os
import re
import datetime
import hashlib
import time
import httpx

from rag_engine.tavily_search import TavilySearcher
from core_engine.config_loader import load_config
from core_engine.logger import get_logger
from core_engine.utils import get_enabled_tools
from core_engine.llm_client import LLMClient

from alibabacloud_bailian20231229.client import Client as BailianClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_bailian20231229 import models as bailian_models

logger = get_logger(__name__)

def main():
    if len(sys.argv) < 2:
        print("用法: python -m core_engine.update_kb <需要补充的知识库主题>")
        sys.exit(1)
        
    topic = sys.argv[1]
    
    print("=" * 60)
    print(f"🤖 [全自动饲养员] 正在为百炼知识库收集营养：【{topic}】")
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
    parser_cfg = cfg.get("parser", {})
    api_key_env = parser_cfg.get("api_key_env", "DASHSCOPE_API_KEY")
    api_key = os.getenv(api_key_env)
    
    if not api_key:
        print(f"错误：缺少环境变量：{api_key_env}")
        sys.exit(1)
        
    print("\n[2/4] 交由 Qwen 模型梳理干货并撰写 Markdown 报告...")
    base_url = parser_cfg.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = parser_cfg.get("model")
    client = LLMClient(
        api_key=api_key, 
        base_url=base_url
    )
    
    materials_text = ""
    for idx, r in enumerate(results, 1):
        materials_text += f"[{idx}] {r.get('title')}\n{r.get('content')}\n\n"
        
    # 指令标准化：定义研究员角色与标准规范（保持静态以优化 Session Cache）
    instructions = (
        "你是一个专业的短剧行业研究员。请针对用户提供的情报素材，整理出一篇结构清晰、极具实战价值的 Markdown 归纳文章。\n"
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
            enable_thinking=bool(parser_cfg.get("tools", {}).get("enable_thinking", True)),
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
        
    print(f"\n[3/4] 高质量资料报告已在本地生成：{file_path}")
    
    # 3. Upload and Index to Bailian
    rag_cfg = cfg.get("rag", {})
    ak = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    sk = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    workspace_id = os.environ.get(rag_cfg.get("workspace_id_env", "WORKSPACE_ID"))
    index_id = os.environ.get(rag_cfg.get("index_id_env", "BAILIAN_INDEX_ID"))
    
    if not all([ak, sk, workspace_id, index_id]):
        print("\n⚠️ 缺少阿里云百炼认证环境 (AK/SK/WORKSPACE_ID/BAILIAN_INDEX_ID)。报告仅保存在本地，未上传知识库。")
        sys.exit(0)
        
    print("\n[4/4] 正在将新生效的报告喂给阿里云百炼知识库...")
    api_config = open_api_models.Config(
        access_key_id=ak,
        access_key_secret=sk,
        endpoint='bailian.cn-beijing.aliyuncs.com'
    )
    bailian_client = BailianClient(api_config)
    
    try:
        size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            md5_hash = hashlib.md5(f.read()).hexdigest()
            
        # 第一步：获取上传通行证 (Lease)
        lease_req = bailian_models.ApplyFileUploadLeaseRequest(
            file_name=filename,
            md_5=md5_hash,
            size_in_bytes=str(size)
        )
        lease_resp = bailian_client.apply_file_upload_lease("default", workspace_id, lease_req)
        upload_url = lease_resp.body.data.param.url
        headers = lease_resp.body.data.param.headers
        lease_id = lease_resp.body.data.file_upload_lease_id
        
        # 第二步：物理上传文件到 OSS
        with open(file_path, "rb") as f:
            with httpx.Client(timeout=60.0) as h_client:
                put_resp = h_client.put(upload_url, headers=headers, content=f)
                if put_resp.status_code != 200:
                    raise RuntimeError(f"OSS 上传返回异常 HTTP {put_resp.status_code}")
                
        # 第三步：注册文件到百炼数据中心
        add_req = bailian_models.AddFileRequest(
            category_id="default",
            lease_id=lease_id,
            parser="DASHSCOPE_DOCMIND"
        )
        add_resp = bailian_client.add_file(workspace_id, add_req)
        file_id = add_resp.body.data.file_id
        print(f"✅ 文件已同步至百炼数据中心 (File ID: {file_id})")
        
        # 第四步：追加文档到原有的知识库 Index 中
        job_req = bailian_models.SubmitIndexAddDocumentsJobRequest(
            index_id=index_id,
            source_type="DATA_CENTER_FILE",
            document_ids=[file_id],
            chunk_size=1500
        )
        job_resp = bailian_client.submit_index_add_documents_job(workspace_id, job_req)
        
        print("\n🎉 知识库饲养成功！")
        print(f"知识切分向量化任务提交完成，流水号 (Job ID: {job_resp.body.data.id})。")
        print("💡 提示：云端需要几分钟时间来切分消化这份文档，稍后您的大模型就能直接读取这份全新血液啦！")
        
    except Exception as e:
        print(f"\n❌ 百炼知识库对接过程出现致命异常：{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

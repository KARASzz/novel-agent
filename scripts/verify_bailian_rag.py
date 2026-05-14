import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify() -> int:
    print("=" * 60)
    print("Initializing BailianRetriever...")

    try:
        from rag_engine.bailian_retriever import BailianRetriever
    except ModuleNotFoundError as exc:
        print("Initialization failed: 百炼 SDK 依赖未安装，无法执行 RAG 连接诊断。")
        print(f"Missing module: {exc.name}")
        print("请先安装 requirements.txt 或补装阿里云百炼相关依赖后再试。")
        return 1

    retriever = BailianRetriever()
    
    if not retriever._client:
        print("Initialization failed: Missing credentials or env vars.")
        print(f"AK: {'YES' if os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID') else 'NO'}")
        print(f"SK: {'YES' if os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET') else 'NO'}")
        print(f"WORKSPACE: {os.environ.get('WORKSPACE_ID', 'NO')}")
        print(f"INDEX_ID: {os.environ.get('BAILIAN_INDEX_ID', 'NO')}")
        return 1

    query = "番茄小说的追读钩子怎么写？"
    print(f"\nQuerying: {query}")
    context = retriever.get_rag_context(query)
    if not context:
        print("\n--- Context Received ---")
        print("未收到有效上下文，百炼连接可能异常。")
        print("------------------------")
        return 1

    print("\n--- Context Received ---")
    print(context)
    print("------------------------")
    print("Done")
    return 0

if __name__ == "__main__":
    raise SystemExit(verify())

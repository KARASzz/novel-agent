import re
import json
import os
from datetime import datetime
from typing import Optional
from core_engine.logger import get_logger

logger = get_logger(__name__)

class ContentCleaner:
    """
    RAG 内容清洗器 (Content Cleaner)
    职责：将原始文本（如 Tavily 搜寻结果或手动录入内容）进行去噪、Markdown 化，并生成关联的元数据文件供检索器使用。
    """

    NOISE_PATTERNS = [
        r'<[^>]+>',                        # HTML 标签
        r'https?://\S+',                   # URL 链接
        r'(点击|关注|转发|收藏|分享).*?(公众号|账号|频道)',  # 推广性干扰词
        r'(广告|推广|赞助).*',              # 广告信息
        r'[\U0001F600-\U0001F9FF]',         # 表情符号 (Emojis)
        r'\n{3,}',                          # 过多的空行
    ]

    def __init__(self, knowledge_base_dir: str, retriever=None):
        self.kb_dir = knowledge_base_dir
        self.retriever = retriever
    
    def _strip_noise(self, raw_text: str) -> str:
        cleaned = raw_text
        for pattern in self.NOISE_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()

    def _generate_metadata(self, title: str, source_url: str, category: str, content_preview: str) -> dict:
        return {
            "title": title,
            "source_url": source_url,
            "category": category,
            "published_date": None,
            "ingested_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "rag_score": None,
            "tags": [],
            "content_preview": content_preview[:200]
        }

    def ingest_tavily_results(self, results: list, category: str = "market_research") -> int:
        """批量导入 Tavily 搜索结果并自动触发检索器索引更新"""
        target_dir = os.path.join(self.kb_dir, category)
        os.makedirs(target_dir, exist_ok=True)
        
        ingested_count = 0
        for idx, result in enumerate(results):
            title = result.get("title", f"Document_{idx}")
            url = result.get("url", "")
            raw_content = result.get("content", "")
            
            if not raw_content or len(raw_content) < 20:
                continue

            cleaned = self._strip_noise(raw_content)
            # 处理 Windows 文件名保留字符，同时防止过于冗长的文件名
            safe_name = re.sub(r'[\\/:*?"<>|]', '_', title)[:60]
            date_prefix = datetime.now().strftime("%Y%m%d")
            filename_base = f"{date_prefix}_{safe_name}"
            
            md_path = os.path.join(target_dir, f"{filename_base}.md")
            md_content = f"# {title}\n\n> Source: {url}\n> Ingested: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n{cleaned}\n"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            meta_path = os.path.join(target_dir, f"{filename_base}.meta.json")
            metadata = self._generate_metadata(title, url, category, cleaned)
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            ingested_count += 1
        
        # 响应式自动索引：内容入库后立即通知检索器重构索引 snapshot
        if ingested_count > 0 and self.retriever:
            logger.info("⚡ [Auto-Indexing] 检测到新知识入库，正在触发 Retriever 索引重建...")
            self.retriever.build_index()
            
        return ingested_count

    def ingest_manual_text(self, title: str, content: str, category: str = "writing_methodology", source_url: str = "Manual") -> str:
        """手动录入文本至知识库"""
        target_dir = os.path.join(self.kb_dir, category)
        os.makedirs(target_dir, exist_ok=True)
        
        cleaned = self._strip_noise(content)
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', title)[:60]
        date_prefix = datetime.now().strftime("%Y%m%d")
        filename_base = f"{date_prefix}_{safe_name}"
        
        md_path = os.path.join(target_dir, f"{filename_base}.md")
        md_content = f"# {title}\n\n> Source: {source_url}\n> Ingested: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n{cleaned}\n"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        meta_path = os.path.join(target_dir, f"{filename_base}.meta.json")
        metadata = self._generate_metadata(title, source_url, category, cleaned)
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        if self.retriever:
            logger.info("⚡ [Auto-Indexing] 手动知识录入完成，正在重建索引...")
            self.retriever.build_index()
            
        return md_path

import math
import os
import re
import threading
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple, cast

from core_engine.config_loader import load_config
from core_engine.logger import get_logger

logger = get_logger(__name__)


class LocalRetriever:
    """轻量级本地混合检索器 (BM25 + 词频重叠)."""

    _INDEX_CACHE: Dict[str, Dict[str, object]] = {}
    _CACHE_LOCK = threading.Lock()
    K1 = 1.5
    B = 0.75

    def __init__(self, knowledge_base_dir: str):
        cfg = load_config()
        rag_cfg = cfg.get("rag", {})

        self.kb_dir = knowledge_base_dir
        self.max_candidates = int(rag_cfg.get("max_candidates", 120))
        self.snippet_chars = int(rag_cfg.get("snippet_chars", 500))

        self.documents: Dict[str, dict] = {}
        self.inverted_index: Dict[str, List[str]] = defaultdict(list)
        self.avg_doc_length: float = 0.0
        self._snapshot: Tuple[Tuple[str, int, int], ...] = tuple()

    def _scan_markdown_files(self) -> List[str]:
        paths: List[str] = []
        for root, _, files in os.walk(self.kb_dir):
            for filename in files:
                if not filename.endswith(".md"):
                    continue
                # 过滤掉知识库说明或占位文件
                if filename == "关于知识库填充.md":
                    continue
                paths.append(os.path.join(root, filename))
        paths.sort()
        return paths

    def _build_snapshot(self, file_paths: List[str]) -> Tuple[Tuple[str, int, int], ...]:
        snapshot = []
        for path in file_paths:
            try:
                stat = os.stat(path)
            except OSError:
                continue
            snapshot.append((path, stat.st_mtime_ns, stat.st_size))
        return tuple(snapshot)

    @staticmethod
    def _bigram_tokenize(text: str) -> List[str]:
        chars = re.findall(r"[\u4e00-\u9fff]", text)
        unigrams = chars[:]
        bigrams = [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]
        english_words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return unigrams + bigrams + english_words

    def build_index(self) -> None:
        file_paths = self._scan_markdown_files()
        snapshot = self._build_snapshot(file_paths)
        cache_key = os.path.abspath(self.kb_dir)
        
        with self._CACHE_LOCK:
            cached = self._INDEX_CACHE.get(cache_key)
            if cached and cached.get("snapshot") == snapshot:
                self.documents = cast(Dict[str, dict], cached["documents"])
                cached_index = cast(Dict[str, List[str]], cached["inverted_index"])
                self.inverted_index = defaultdict(list, cached_index)
                self.avg_doc_length = float(cast(float, cached["avg_doc_length"]))
                self._snapshot = snapshot
                logger.info("Retriever 索引缓存命中: %s docs", len(self.documents))
                return

        self.documents = {}
        self.inverted_index = defaultdict(list)
        total_length = 0

        for idx, filepath in enumerate(file_paths):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue

            rel_dir = os.path.relpath(os.path.dirname(filepath), self.kb_dir)
            category = rel_dir.split(os.sep)[0] if rel_dir != "." else "未分类"
            
            # --- 基于标题的分块 (Header-based Chunking) ---
            chunks = re.split(r"(^#+\s+.+)", content, flags=re.MULTILINE)
            
            current_title = os.path.basename(filepath)
            
            processed_chunks = []
            if chunks[0].strip():
                processed_chunks.append((current_title, chunks[0].strip()))
            
            for i in range(1, len(chunks), 2):
                header = chunks[i].strip("# ").strip()
                body = chunks[i+1].strip() if i+1 < len(chunks) else ""
                processed_chunks.append((header, body))

            for c_idx, (c_title, c_body) in enumerate(processed_chunks):
                if not c_body.strip() and not c_title.strip():
                    continue
                
                doc_id = f"doc_{idx}_{c_idx}"
                full_chunk_text = f"{c_title}\n{c_body}"
                tokens = self._bigram_tokenize(full_chunk_text)
                tf_counter = Counter(tokens)
                
                self.documents[doc_id] = {
                    "path": filepath,
                    "title": c_title,
                    "file_title": current_title,
                    "content": c_body,
                    "tokens": tokens,
                    "tf_counter": tf_counter,
                    "length": len(tokens),
                    "category": category,
                }
                for token in tf_counter.keys():
                    self.inverted_index[token].append(doc_id)
                total_length += len(tokens)

        doc_count = max(len(self.documents), 1)
        self.avg_doc_length = total_length / doc_count
        self._snapshot = snapshot

        with self._CACHE_LOCK:
            self._INDEX_CACHE[cache_key] = {
                "snapshot": snapshot,
                "documents": self.documents,
                "inverted_index": dict(self.inverted_index),
                "avg_doc_length": self.avg_doc_length,
            }
        logger.info(
            "Retriever 索引构建完成: docs=%s avg_doc_len=%.0f vocab=%s",
            len(self.documents),
            self.avg_doc_length,
            len(self.inverted_index),
        )

    def _bm25_score(self, query_tokens: List[str], doc_id: str) -> float:
        doc = self.documents[doc_id]
        tf_counter: Counter = doc["tf_counter"]
        doc_len = max(int(doc["length"]), 1)
        avg_len = max(self.avg_doc_length, 1.0)
        total_docs = len(self.documents)
        score = 0.0

        for token in query_tokens:
            postings = self.inverted_index.get(token)
            if not postings:
                continue
            df = len(postings)
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1)
            tf = tf_counter.get(token, 0)
            numerator = tf * (self.K1 + 1)
            denominator = tf + self.K1 * (1 - self.B + self.B * doc_len / avg_len)
            if denominator > 0:
                score += idf * (numerator / denominator)
        return score

    def _candidate_docs(
        self,
        query_tokens: List[str],
        category_filter: Optional[str] = None,
    ) -> List[str]:
        token_set = set(query_tokens)
        if not token_set:
            return []

        overlap: Counter[str] = Counter()
        for token in token_set:
            for doc_id in self.inverted_index.get(token, []):
                if category_filter and self.documents[doc_id]["category"] != category_filter:
                    continue
                overlap[doc_id] += 1

        if not overlap:
            return []
        return [doc_id for doc_id, _ in overlap.most_common(self.max_candidates)]

    def search(
        self,
        query: str,
        top_k: int = 3,
        category_filter: Optional[str] = None,
    ) -> List[Tuple[float, str, str, str]]:
        if not self.documents:
            logger.warning("Retriever 索引为空。请先调用 build_index()。")
            return []

        query_tokens = self._bigram_tokenize(query)
        candidates = self._candidate_docs(query_tokens, category_filter=category_filter)
        if not candidates:
            return []

        scored_docs = []
        for doc_id in candidates:
            score = self._bm25_score(query_tokens, doc_id)
            if score > 0:
                scored_docs.append((score, doc_id))
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, doc_id in scored_docs[:top_k]:
            doc = self.documents[doc_id]
            limit = max(self.snippet_chars, 2000)
            snippet = doc["content"][:limit].strip()
            results.append((round(score, 3), doc["title"], doc["category"], snippet))
        return results

    def get_rag_context(self, query: str, top_k: int = 3) -> str:
        results = self.search(query, top_k=top_k)
        if not results:
            return "[RAG 知识库未找到相关参考资料]"

        lines = ["以下是从本地知识库检索到的业务约束与爆款参考，请在生成剧本时严格参考：\n"]
        for idx, (score, title, category, snippet) in enumerate(results, start=1):
            lines.append(f"### [知识条目 {idx}] (相关度: {score})")
            lines.append(f"内容来源: {category} > {title}")
            lines.append(f"具体规则:\n{snippet}\n")
        return "\n".join(lines)


class HybridRetriever:
    """双引擎检索器，支持自动降级 (Fallback)。优先百炼远程知识库，失败则使用本地 BM25。"""
    def __init__(self, local_kb_dir: str, remote_retriever=None):
        self.local = LocalRetriever(local_kb_dir)
        self.remote = remote_retriever
        self.last_fallback_reason: Optional[str] = None
        self.local.build_index()

    def build_index(self):
        """重新扫描并构建本地索引"""
        self.local.build_index()

    def search(self, query: str, top_k: int = 3, category_filter: Optional[str] = None):
        self.last_fallback_reason = None
        if self.remote:
            try:
                results = self.remote.search(query, top_k=top_k)
                if results:
                    return results
                self.last_fallback_reason = "remote_empty_result"
                logger.info("远程 RAG 返回空结果，自动切换至本地检索。")
            except Exception as e:
                self.last_fallback_reason = f"remote_exception:{type(e).__name__}"
                logger.warning(f"远程 RAG 检索异常: {e}。自动回退到本地。")
        
        return self.local.search(query, top_k=top_k, category_filter=category_filter)

    def get_rag_context(self, query: str, top_k: int = 3) -> str:
        self.last_fallback_reason = None
        if self.remote:
            try:
                res = self.remote.search(query, top_k=top_k)
                if res:
                    lines = ["以下是从 [阿里云百炼远程知识库] 检索到的业务约束与爆款参考：\n"]
                    for idx, (score, title, category, snippet) in enumerate(res, start=1):
                        lines.append(f"### [远程知识条目 {idx}] (相关度: {score})")
                        lines.append(f"内容来源: {category} > {title}")
                        lines.append(f"具体规则:\n{snippet}\n")
                    return "\n".join(lines)
                self.last_fallback_reason = "remote_empty_result"
                logger.info("远程 RAG 上下文生成为空，自动切换至本地。")
            except Exception as e:
                self.last_fallback_reason = f"remote_exception:{type(e).__name__}"
                logger.warning(f"远程 RAG 上下文生成失败: {e}。回退到本地。")

        return self.local.get_rag_context(query, top_k=top_k)

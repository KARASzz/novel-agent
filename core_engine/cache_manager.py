import hashlib
import json
import os
import tempfile
import threading
import time
from typing import Any, Dict, Optional

class CacheManager:
    """
    剧本解析结果缓存管理器 (Cache Manager)
    职责：为每一个剧本文件（基于 MD5 内容指纹）存储解析后的 JSON 结构，避免重复调用 LLM 造成 Token 浪费。
    支持“精准清理”功能，允许根据剧本标题关键词批量删除特定缓存。
    """
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self._write_lock = threading.Lock()

    def _get_hash(self, content: str, salt: str = "") -> str:
        """
        计算内容的指纹哈希。
        由于不同题材的剧本内容可能雷同，建议配置时加入基于 Prompt 版本的 salt。
        """
        combined = f"{content}:{salt}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _compute_rag_fingerprint(self, rag_query: Optional[str]) -> str:
        """计算 RAG 查询指纹，用于 RAG 场景下缓存 key 的区分"""
        if not rag_query:
            return ""
        return hashlib.sha256(rag_query[:50].encode("utf-8")).hexdigest()[:8]

    @staticmethod
    def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        兼容旧格式缓存：
        - 旧格式: 直接是 episode 字典
        - 新格式: {"meta": {...}, "data": episode_dict}
        """
        if "data" in payload and isinstance(payload.get("data"), dict):
            return payload
        return {
            "meta": {
                "created_at": 0.0,
                "ttl_seconds": None,
                "version": 1,
            },
            "data": payload,
        }

    @staticmethod
    def _is_expired(meta: Dict[str, Any]) -> bool:
        created_at = float(meta.get("created_at", 0.0) or 0.0)
        ttl_seconds = meta.get("ttl_seconds")
        if ttl_seconds is None:
            return False
        try:
            ttl_seconds = int(ttl_seconds)
        except (TypeError, ValueError):
            return False
        if ttl_seconds <= 0:
            return False
        return (time.time() - created_at) > ttl_seconds

    def get_cache(self, content: str, salt: str = "", rag_query: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取缓存的 JSON 结构，rag_query 用于 RAG 场景下的缓存区分"""
        if rag_query:
            salt = f"{salt}:{self._compute_rag_fingerprint(rag_query)}"
        cache_id = self._get_hash(content, salt)
        cache_file = os.path.join(self.cache_dir, f"{cache_id}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                normalized = self._normalize_payload(payload)
                if self._is_expired(normalized.get("meta", {})):
                    try:
                        os.remove(cache_file)
                    except Exception:
                        pass
                    return None
                return normalized.get("data")
            except Exception:
                return None
        return None

    def set_cache(
        self,
        content: str,
        data: Dict[str, Any],
        salt: str = "",
        rag_query: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """持久化缓存，rag_query 用于 RAG 场景下的缓存区分"""
        if rag_query:
            salt = f"{salt}:{self._compute_rag_fingerprint(rag_query)}"
        cache_id = self._get_hash(content, salt)
        cache_file = os.path.join(self.cache_dir, f"{cache_id}.json")
        
        try:
            payload = {
                "meta": {
                    "created_at": time.time(),
                    "ttl_seconds": ttl_seconds,
                    "version": 1,
                },
                "data": data,
            }
            # 使用同目录临时文件 + replace，避免并发写入导致半文件。
            with self._write_lock:
                fd, tmp_file = tempfile.mkstemp(prefix="cache_", suffix=".tmp", dir=self.cache_dir)
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                    os.replace(tmp_file, cache_file)
                finally:
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
        except Exception:
            pass

    def clear_cache(self, filter_keyword: Optional[str] = None) -> int:
        """
        批量清理缓存快照。
        支持传入 filter_keyword，只删除 JSON 内容中 'title' 字段包含该关键词的缓存文件。
        如果不传，则清空整个目录。
        """
        count = 0
        if not os.path.exists(self.cache_dir):
            return 0
            
        for f_name in os.listdir(self.cache_dir):
            if not f_name.endswith(".json"):
                continue
                
            file_path = os.path.join(self.cache_dir, f_name)
            if filter_keyword:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        payload = self._normalize_payload(json.load(f))
                        title = payload.get("data", {}).get("title", "")
                        if filter_keyword.lower() not in title.lower():
                            continue
                except Exception:
                    continue

            try:
                os.remove(file_path)
                count += 1
            except Exception:
                pass
        return count

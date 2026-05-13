"""
Layer0: 信源净化与时效校准

核心职责：
1. 时间戳校验 - 禁止使用过期数据
2. 信源分级 - 官方/主流/第三方/行业/自媒体分层打权重
3. 事实/观点分桶 - 区分客观事实和主观观点
4. 热度口径归一 - 日活/月活/观看量等分开统计
5. 内容形态打标 - 真人短剧/AI奇观/混合
6. 风险信号提取 - 肖像/IP/合规风险
"""
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pre_hub.schemas.pre_hub_models import (
    Layer0Output,
    SourceConfidenceItem,
    SourceTier,
)


class SourceCleaner:
    """信源净化器"""

    # 各信源层级默认置信度
    TIER_CONFIDENCE = {
        SourceTier.OFFICIAL: 0.95,
        SourceTier.MAINSTREAM: 0.80,
        SourceTier.THIRD_PARTY: 0.70,
        SourceTier.INDUSTRY: 0.50,
        SourceTier.SELF_MEDIA: 0.30,
    }

    # 风险关键词
    RISK_KEYWORDS = [
        "侵权", "抄袭", "盗版", "未经授权",
        "肖像权", "脸模", "声音",
        "改编权", "IP归属", "版权纠纷",
        "平台处罚", "下架", "封禁",
        "敏感题材", "违规内容", "擦边",
    ]

    # 内容形态关键词
    FORMAT_KEYWORDS = {
        "真人": ["真人短剧", "真人剧", "实拍", "演员"],
        "AI奇观": ["AI生成", "AI动画", "AI漫剧", "虚拟形象", "AI建模"],
        "混合": ["真人+AI", "AI辅助", "混合制作"],
    }

    def __init__(self, min_published_days: int = 90):
        """
        Args:
            min_published_days: 禁止使用多少天前的数据，默认90天
        """
        self.min_published_days = min_published_days
        self.cutoff_date = datetime.now() - timedelta(days=min_published_days)

    def clean(self, raw_search_results: List[Dict[str, Any]]) -> Layer0Output:
        """
        对原始搜索结果进行净化

        Args:
            raw_search_results: Tavily搜索返回的原始结果列表

        Returns:
            Layer0Output: 净化后的数据包
        """
        cleaned_sources = []
        source_confidence_map = []
        metric_normalization_note = {}
        content_form_tags = set()
        rights_risk_signals = []

        for result in raw_search_results:
            # 1. 时间戳校验
            published_at = result.get("published_at") or result.get("date")
            if not self._check_time_valid(published_at):
                continue  # 跳过过期数据

            # 2. 信源分级
            source_name = result.get("source", "unknown")
            tier = self._classify_tier(source_name, result.get("url", ""))
            confidence = self.TIER_CONFIDENCE.get(tier, 0.3)

            # 3. 事实/观点分桶
            is_fact, fact_content = self._separate_fact_opinion(
                result.get("content", ""), tier
            )

            # 4. 内容形态打标
            form_tags = self._detect_format(result.get("content", ""))
            content_form_tags.update(form_tags)

            # 5. 风险信号提取
            risks = self._extract_risk_signals(result.get("content", ""))
            rights_risk_signals.extend(risks)

            # 构建净化后数据
            cleaned_item = {
                "title": result.get("title", ""),
                "content": fact_content if is_fact else result.get("content", ""),
                "url": result.get("url", ""),
                "source": source_name,
                "tier": tier.value,
                "confidence": confidence,
                "published_at": published_at,
                "is_fact": is_fact,
                "format_tags": list(form_tags),
                "risk_signals": risks,
            }
            cleaned_sources.append(cleaned_item)

            # 构建信源可信度图
            source_confidence_map.append(SourceConfidenceItem(
                source_name=source_name,
                source_tier=tier,
                confidence=confidence,
                published_at=published_at,
                is_fact=is_fact,
            ))

        # 热度口径归一说明
        metric_normalization_note = {
            "DAU_vs_月活": "需分开统计，不可混用",
            "热度值_vs_分账": "口径不同，需归一化处理",
            "观看量_vs_观看人次": "同一用户多次观看计为多次vs去重",
        }

        return Layer0Output(
            cleaned_sources=cleaned_sources,
            source_confidence_map=source_confidence_map,
            metric_normalization_note=metric_normalization_note,
            content_form_tags=list(content_form_tags),
            rights_risk_signals=list(set(rights_risk_signals)),
        )

    def _check_time_valid(self, published_at: Optional[str]) -> bool:
        """检查时间戳是否有效"""
        if not published_at:
            return False

        try:
            # 尝试解析多种日期格式
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(published_at[:10], fmt)
                    return dt >= self.cutoff_date
                except ValueError:
                    continue

            # 如果是相对时间（如"3天前"）
            relative_match = re.search(r"(\d+)\s*天前", published_at)
            if relative_match:
                days_ago = int(relative_match.group(1))
                return days_ago <= self.min_published_days

            return False
        except Exception:
            return False

    def _classify_tier(self, source_name: str, url: str) -> SourceTier:
        """根据来源名称和URL分类信源层级"""
        source_lower = source_name.lower()
        url_lower = url.lower()

        # 官方平台
        official_patterns = ["官方", "official", "平台公告", "官方账号"]
        if any(p in source_lower or p in url_lower for p in official_patterns):
            return SourceTier.OFFICIAL

        # 主流媒体
        mainstream_patterns = [
            "新浪", "腾讯", "网易", "搜狐", "凤凰",
            "人民日报", "新华社", "央视",
            "weibo.com", "qq.com", "163.com",
        ]
        if any(p in source_lower or p in url_lower for p in mainstream_patterns):
            return SourceTier.MAINSTREAM

        # 第三方数据机构
        third_party_patterns = [
            "数据", "研究院", "咨询", "报告",
            "克劳锐", "艾瑞", "易观", "QuestMobile",
        ]
        if any(p in source_lower or p in url_lower for p in third_party_patterns):
            return SourceTier.THIRD_PARTY

        # 行业媒体
        industry_patterns = [
            "36氪", "虎嗅", "钛媒体", "雷峰网",
            "industry", "media",
        ]
        if any(p in source_lower or p in url_lower for p in industry_patterns):
            return SourceTier.INDUSTRY

        return SourceTier.SELF_MEDIA

    def _separate_fact_opinion(self, content: str, tier: SourceTier) -> Tuple[bool, str]:
        """
        分离事实和观点内容

        Returns:
            (is_fact, processed_content)
        """
        if not content:
            return False, content

        # 高可信度来源（官方/主流）的默认当事实
        if tier in [SourceTier.OFFICIAL, SourceTier.MAINSTREAM]:
            return True, content

        # 自媒体内容需要更严格校验
        opinion_markers = [
            "我觉得", "我认为", "个人感觉",
            "应该会", "大概", "可能", "也许",
            "太牛了", "太棒了", "绝绝子",
            "爆了", "彻底", "完全",
        ]

        has_opinion = any(marker in content for marker in opinion_markers)

        if has_opinion and tier == SourceTier.SELF_MEDIA:
            # 尝试提取客观部分
            sentences = content.split("。")
            fact_sentences = [
                s for s in sentences
                if not any(m in s for m in opinion_markers)
            ]
            if fact_sentences:
                return True, "。".join(fact_sentences)
            return False, content

        return True, content

    def _detect_format(self, content: str) -> List[str]:
        """检测内容形态"""
        tags = []
        content_lower = content.lower()

        for format_name, keywords in self.FORMAT_KEYWORDS.items():
            if any(kw in content_lower for kw in keywords):
                if format_name == "真人":
                    tags.append("真人短剧")
                elif format_name == "AI奇观":
                    tags.append("AI奇观")
                elif format_name == "混合":
                    tags.append("真人+AI混合")

        return list(set(tags))

    def _extract_risk_signals(self, content: str) -> List[str]:
        """提取风险信号"""
        risks = []
        content_lower = content.lower()

        for keyword in self.RISK_KEYWORDS:
            if keyword in content_lower:
                risks.append(keyword)

        return list(set(risks))


class ContentNormalizer:
    """热度口径归一处理器"""

    METRIC_PATTERNS = {
        "DAU": [r"日活[：:]?\s*(\d+)", r"DAU[：:]?\s*(\d+)"],
        "MAU": [r"月活[：:]?\s*(\d+)", r"MAU[：:]?\s*(\d+)"],
        "观看量": [r"观看[量次个]+[：:]?\s*(\d+)", r"播放[量次]+[：:]?\s*(\d+)"],
        "热度值": [r"热度值[：:]?\s*(\d+)", r"热度[：:]?\s*(\d+)"],
        "分账": [r"分账[额元]+[：:]?\s*(\d+)", r"分账[：:]?\s*(\d+)"],
    }

    def normalize(self, content: str) -> Dict[str, Any]:
        """
        提取并归一化各类指标

        Returns:
            dict: {metric_name: [(value, source), ...]}
        """
        result = {}

        for metric, patterns in self.METRIC_PATTERNS.items():
            values = []
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    try:
                        value = int(match)
                        values.append(value)
                    except (ValueError, TypeError):
                        pass

            if values:
                result[metric] = values

        return result

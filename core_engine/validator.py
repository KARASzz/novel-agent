from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FanqieChapterValidationReport:
    """番茄小说单章质检报告。"""
    chapter_index: int
    chapter_title: str
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    score: int
    word_count: int
    checks: dict


class FanqieChapterValidator:
    """
    番茄小说章节质检器 (轻量化版本)。

    定位：客观物理指标检查 + 语义特征统计。
    不再进行机械化的扣分。
    """

    AI_TONE_PATTERNS = (
        "总之", "可以说", "不难看出", "由此可见", "在这个过程中",
        "情绪价值", "命运的齿轮", "他深深地明白",
    )
    ABSTRACT_PATTERNS = (
        "这是一种", "某种意义上", "无疑", "显然", "内心深处",
        "复杂的情绪", "无法用语言形容",
    )
    CONFLICT_PATTERNS = (
        "逼", "夺", "抢", "拦", "砸", "威胁", "反击", "质问",
        "冲突", "代价", "羞辱", "真相",
    )
    PAYOFF_PATTERNS = (
        "打脸", "反击", "赢", "翻盘", "报复", "升级", "突破",
        "爽", "兑现", "压回去",
    )
    HOOK_PATTERNS = (
        "突然", "却", "没想到", "下一刻", "门外", "电话",
        "短信", "真相", "名单", "证据", "代价", "章尾钩子",
    )

    def __init__(
        self,
        min_words: int = 800,
        max_words: int = 6000,
        ai_tone_limit: int = 2,
        long_paragraph_limit: int = 900,
    ) -> None:
        self.min_words = min_words
        self.max_words = max_words
        self.ai_tone_limit = ai_tone_limit
        self.long_paragraph_limit = long_paragraph_limit

    @staticmethod
    def _word_count(text: str) -> int:
        return len("".join(text.split()))

    @staticmethod
    def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
        return any(pattern in text for pattern in patterns)

    @staticmethod
    def _count_patterns(text: str, patterns: tuple[str, ...]) -> int:
        return sum(text.count(pattern) for pattern in patterns)

    def validate(
        self,
        chapter_text: str,
        chapter_index: int = 1,
        chapter_title: str = "",
        previous_writeback: str = "",
        expected_characters: Optional[List[str]] = None,
        required_setting_terms: Optional[List[str]] = None,
    ) -> FanqieChapterValidationReport:
        text = chapter_text.strip()
        errors: List[str] = []
        warnings: List[str] = []
        
        # 统计物理指标
        word_count = self._word_count(text)
        if not text:
            errors.append("章节正文为空。")
            return FanqieChapterValidationReport(chapter_index, chapter_title, False, errors, warnings, 0, 0, {})

        # 字数建议 (仅参考)
        if word_count < self.min_words:
            warnings.append(f"字数偏低（{word_count}），建议番茄起步不少于 {self.min_words} 字。")
        elif word_count > self.max_words:
            warnings.append(f"字数偏高（{word_count}），注意节奏把控。")

        # 承接性检查
        opening = text[:300]
        opening_continuity = chapter_index <= 1 or bool(previous_writeback and self._contains_any(opening, ("上一章", "刚才", "方才", "还没", "继续", "承接", "代价", "伤口", "证据")))
        if chapter_index > 1 and not opening_continuity:
            warnings.append("建议加强开章承接感。")

        # 语义特征初步提取 (仅供参考，不作为绝对标准)
        conflict_signals = self._count_patterns(text, self.CONFLICT_PATTERNS)
        payoff_signals = self._count_patterns(text, self.PAYOFF_PATTERNS)
        
        ending = text[-260:]
        ending_hook_signals = self._contains_any(ending, self.HOOK_PATTERNS) or ending.rstrip().endswith(("？", "!", "！", "……"))

        # 人物与设定自检
        expected_characters = expected_characters or []
        missing_characters = [name for name in expected_characters if name and name not in text]
        if missing_characters:
            warnings.append(f"预期人物未显化: {', '.join(missing_characters)}")

        required_setting_terms = required_setting_terms or []
        missing_settings = [term for term in required_setting_terms if term and term not in text]
        if missing_settings:
            warnings.append(f"关键设定词缺失: {', '.join(missing_settings)}")

        # 风格指标
        ai_tone_count = self._count_patterns(text, self.AI_TONE_PATTERNS)
        abstract_count = self._count_patterns(text, self.ABSTRACT_PATTERNS)
        
        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
        long_paragraphs = [p for p in paragraphs if len(p) > self.long_paragraph_limit]

        # 现在的评分逻辑：不再暴力扣分，而是基于“是否存在严重物理缺失”和“基本合规性”
        # 真正的质量交给后续的 LLM 对抗验证。
        is_pass = not errors and word_count >= (self.min_words * 0.7)
        
        # 启发式总分 (仅供仪表盘参考)
        heuristic_score = 100
        if not opening_continuity: heuristic_score -= 5
        if conflict_signals == 0: heuristic_score -= 10
        if not ending_hook_signals: heuristic_score -= 10
        if ai_tone_count > self.ai_tone_limit: heuristic_score -= 10
        if long_paragraphs: heuristic_score -= 5
        
        checks = {
            "word_count_ok": word_count >= self.min_words,
            "opening_continuity": opening_continuity,
            "conflict_signals": conflict_signals,
            "payoff_signals": payoff_signals,
            "ending_hook": ending_hook_signals,
            "character_check": not missing_characters,
            "style_ai_tone_count": ai_tone_count,
            "style_long_paragraphs": len(long_paragraphs),
        }

        return FanqieChapterValidationReport(
            chapter_index=chapter_index,
            chapter_title=chapter_title,
            is_valid=is_pass,
            errors=errors,
            warnings=warnings,
            score=max(0, heuristic_score),
            word_count=word_count,
            checks=checks,
        )


def run_self_test(config: Optional[dict] = None) -> FanqieChapterValidationReport:
    sample = (
        "第一章：旧站台的电话\n"
        "上一章留下的证据还在掌心发烫，林照把纸条攥紧，刚踏进旧站台，就被债主的人堵在检票口。"
        "对方逼他交出名单，还当众夺走母亲留下的怀表。林照没有退，他反手把录音笔按开，"
        "让所有人都听见对方威胁孤儿院的证据。人群一下炸开，债主脸色铁青。"
        "林照终于把第一口恶气压回去，可电话突然响起，屏幕上只有一句话：真正的名单，在你父亲坟前。"
    )
    report = FanqieChapterValidator(min_words=80).validate(
        sample,
        chapter_index=1,
        chapter_title="第一章：旧站台的电话",
    )

    print("\n" + "=" * 10 + " 番茄小说章节质检结果 (重构版) " + "=" * 10)
    print(f"当前章节: 第 {report.chapter_index} 章 {report.chapter_title}")
    print(f"校验状态: {'✅ 通过' if report.is_valid else '❌ 存在问题'}")
    print(f"质量评分 (参考): {report.score} 分")
    print(f"字数估算: {report.word_count}")

    if report.errors:
        print("\n❌ 发现关键错误 (ERRORS):")
        for err in report.errors:
            print("  -", err)

    if report.warnings:
        print("\n⚠️ 优化建议 (WARNINGS):")
        for wrn in report.warnings:
            print("  -", wrn)
    print("=" * 38 + "\n")

    return report


if __name__ == "__main__":
    run_self_test()

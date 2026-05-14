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
    番茄小说章节质检器。

    面向网文章节正文，检查章节字数、开章承接、冲突推进、爽点外化、
    章尾追读钩子、人物行为一致性、设定连续性，以及 AI 腔、空话、
    解释过度和节奏拖沓。
    """

    AI_TONE_PATTERNS = (
        "总之",
        "可以说",
        "不难看出",
        "由此可见",
        "在这个过程中",
        "情绪价值",
        "命运的齿轮",
        "他深深地明白",
    )
    ABSTRACT_PATTERNS = (
        "这是一种",
        "某种意义上",
        "无疑",
        "显然",
        "内心深处",
        "复杂的情绪",
        "无法用语言形容",
    )
    CONFLICT_PATTERNS = (
        "逼",
        "夺",
        "抢",
        "拦",
        "砸",
        "威胁",
        "反击",
        "质问",
        "冲突",
        "代价",
        "羞辱",
        "真相",
    )
    PAYOFF_PATTERNS = (
        "打脸",
        "反击",
        "赢",
        "翻盘",
        "报复",
        "升级",
        "突破",
        "爽",
        "兑现",
        "压回去",
    )
    HOOK_PATTERNS = (
        "突然",
        "却",
        "没想到",
        "下一刻",
        "门外",
        "电话",
        "短信",
        "真相",
        "名单",
        "证据",
        "代价",
        "章尾钩子",
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
        # 中文网文按非空白字符粗估，避免英文分词把中文整段算作一个词。
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
        score = 100

        word_count = self._word_count(text)
        if not text:
            errors.append("章节正文为空。")
            return FanqieChapterValidationReport(chapter_index, chapter_title, False, errors, warnings, 0, 0, {})

        if word_count < self.min_words:
            errors.append(f"章节字数偏短：{word_count}，低于番茄章节建议下限 {self.min_words}。")
            score -= 25
        elif word_count > self.max_words:
            warnings.append(f"章节字数偏长：{word_count}，高于建议上限 {self.max_words}，可能影响移动端阅读节奏。")
            score -= 10

        opening = text[:300]
        ending = text[-260:]
        opening_continuity = chapter_index <= 1 or bool(previous_writeback and self._contains_any(opening, ("上一章", "刚才", "方才", "还没", "继续", "承接", "代价", "伤口", "证据")))
        if chapter_index > 1 and not opening_continuity:
            warnings.append("开章承接不足：当前章开头没有明显回应上一章回写或上一章后果。")
            score -= 8

        conflict_progression = self._contains_any(text, self.CONFLICT_PATTERNS)
        if not conflict_progression:
            errors.append("冲突推进不足：正文缺少明确阻力、代价、质问、反击或真相推进。")
            score -= 18

        payoff_externalized = self._contains_any(text, self.PAYOFF_PATTERNS)
        if not payoff_externalized:
            warnings.append("爽点外化不足：缺少可感知的打脸、反击、翻盘、升级或兑现动作。")
            score -= 10

        ending_hook = self._contains_any(ending, self.HOOK_PATTERNS) or ending.rstrip().endswith(("？", "!", "！", "……"))
        if not ending_hook:
            errors.append("章尾追读钩子不足：结尾没有留下可追读的问题、代价、证据、反转或强悬念。")
            score -= 20

        expected_characters = expected_characters or []
        missing_characters = [name for name in expected_characters if name and name not in text]
        if missing_characters:
            warnings.append(f"人物行为一致性风险：预期人物未出场或未被明确提及：{', '.join(missing_characters)}。")
            score -= min(12, len(missing_characters) * 4)

        required_setting_terms = required_setting_terms or []
        missing_settings = [term for term in required_setting_terms if term and term not in text]
        if missing_settings:
            warnings.append(f"设定连续性风险：缺少关键设定词：{', '.join(missing_settings)}。")
            score -= min(12, len(missing_settings) * 4)

        ai_tone_count = self._count_patterns(text, self.AI_TONE_PATTERNS)
        if ai_tone_count > self.ai_tone_limit:
            warnings.append(f"AI腔风险：检测到 {ai_tone_count} 处模板化表达，建议改成具体动作、感官和对白。")
            score -= min(16, ai_tone_count * 3)

        abstract_count = self._count_patterns(text, self.ABSTRACT_PATTERNS)
        if abstract_count >= 3:
            warnings.append(f"空话/抽象总结偏多：检测到 {abstract_count} 处抽象解释，建议改为具体事件和身体反应。")
            score -= min(12, abstract_count * 2)

        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
        long_paragraphs = [p for p in paragraphs if len(p) > self.long_paragraph_limit]
        if long_paragraphs:
            warnings.append(f"节奏拖沓风险：存在 {len(long_paragraphs)} 段超长段落，建议拆分并增加动作/对白节拍。")
            score -= min(10, len(long_paragraphs) * 3)

        checks = {
            "word_count_in_range": self.min_words <= word_count <= self.max_words,
            "opening_continuity": opening_continuity,
            "conflict_progression": conflict_progression,
            "payoff_externalized": payoff_externalized,
            "ending_hook": ending_hook,
            "character_consistency": not missing_characters,
            "setting_continuity": not missing_settings,
            "ai_tone_ok": ai_tone_count <= self.ai_tone_limit,
            "abstract_summary_ok": abstract_count < 3,
            "pacing_ok": not long_paragraphs,
        }

        score = max(0, min(100, score))
        return FanqieChapterValidationReport(
            chapter_index=chapter_index,
            chapter_title=chapter_title,
            is_valid=not errors and score >= 60,
            errors=errors,
            warnings=warnings,
            score=score,
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

    print("\n" + "=" * 10 + " 番茄小说章节质检结果 " + "=" * 10)
    print(f"当前章节: 第 {report.chapter_index} 章 {report.chapter_title}")
    print(f"校验状态: {'✅ 通过' if report.is_valid else '❌ 存在问题'}")
    print(f"质量评分: {report.score} 分")
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

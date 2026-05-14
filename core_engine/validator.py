import math
from dataclasses import dataclass
from typing import List, Optional

# 导入项目定义的模型架构
from core_engine.schemas import Episode, Plot, Scene
from core_engine.config_loader import load_config

@dataclass
class ValidationReport:
    """剧本单集校验报告 (用于批处理生成后的质量评估报告)"""
    episode_number: int
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    format_score: int


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

class FormatValidator:
    """
    历史 Episode 结构校验器 (Format Validator)。

    保留给旧批处理链路使用；番茄小说章节默认使用 FanqieChapterValidator。
    这里只维护旧 JSON 结构、时长估算和结尾钩子检查的兼容行为。
    """
    
    def __init__(
        self,
        config: Optional[dict] = None,
        min_duration_sec: Optional[int] = None,
        max_duration_sec: Optional[int] = None,
        speech_rate: Optional[float] = None,
    ):
        """
        初始化校验器配置。建议由外部传入统一加载好的 config 对象，以减少 I/O。
        """
        self.config = config if config else load_config()
        self.validator_cfg = self.config.get("validator", {})
        self.scoring = self.config.get("scoring", {})

        self.min_duration_sec = min_duration_sec if min_duration_sec is not None else self.validator_cfg.get("min_duration_sec", 60)
        self.max_duration_sec = max_duration_sec if max_duration_sec is not None else self.validator_cfg.get("max_duration_sec", 150)
        self.speech_rate = speech_rate if speech_rate is not None else self.validator_cfg.get("speech_rate", 4.5)

    def _estimate_plot_duration(self, plot: Plot) -> int:
        """估算单条剧情 (Plot) 的口播时长，基于语速常数和动作复杂性估算。"""
        if plot.duration_sec:
            return plot.duration_sec
        
        clen = len(plot.content)
        if plot.type in ["dialogue", "os", "monologue"]:
            return max(1, math.ceil(clen / self.speech_rate))
        elif plot.type == "action":
            # 动作通常伴随画面，估算略长
            return max(2, math.ceil(clen / 4.0) + 1)
        return 1

    def validate(self, episode: Episode) -> ValidationReport:
        errors: List[str] = []
        warnings: List[str] = []
        score = 100
        
        # 1. 剧本基本结构审查 (确保场景列表不为空且格式符合预期)
        if not episode.scenes:
            errors.append("剧本内容不包含有效的场景列表 (Scenes) 结构。")
            return ValidationReport(episode.episode_number, False, errors, warnings, 0)
            
        total_duration = 0
        has_hook_at_end = False
        
        # 遍历场景与情节计算时长及检查结尾钩子 (Plot)
        last_plot = None
        for scene in episode.scenes:
            for plot in scene.plots:
                total_duration += self._estimate_plot_duration(plot)
                last_plot = plot

        # 2. 旧单集时长边界校验
        if total_duration < self.min_duration_sec:
            warnings.append(f"单集预估时长偏短: {total_duration} 秒。建议增加描述性情节或对话。")
            score -= self.scoring.get("duration_short_penalty", 10)
        elif total_duration > self.max_duration_sec:
            errors.append(f"单集预估时长超标: {total_duration} 秒。建议最高 {self.max_duration_sec} 秒，过长可能导致节奏拖沓。")
            score -= self.scoring.get("duration_long_penalty", 30)

        # 3. 剧本钩子 (Hook) 检测
        if last_plot:
            has_hook_at_end = last_plot.is_cliffhanger
        
        if not has_hook_at_end:
            warnings.append("剧本结尾缺少钩子情节 (is_cliffhanger=False)，可能会降低观众的下一集留存率。")
            score -= self.scoring.get("no_hook_penalty", 15)

        # 4. 旧单集强卡点逻辑检查
        if episode.is_paywall:
            if not has_hook_at_end:
                errors.append("旧单集卡点必须包含强力结尾钩子。")
                score -= self.scoring.get("paywall_no_hook_penalty", 40)

        # 5. 黄金三集审核 (第 1-3 集必须强制包含高能反转/钩子)
        if episode.episode_number <= 3:
            if not has_hook_at_end:
                errors.append("黄金前三集必须包含核心反转或强力钩子卡点，这是提升剧本整体转化率的关键，建议增加剧情密度和冲突强度。")
                score -= self.scoring.get("first3_no_hook_penalty", 20)

        is_valid = len(errors) == 0
        score = max(0, min(100, score))

        return ValidationReport(
            episode_number=episode.episode_number,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            format_score=score
        )


def build_self_test_episode() -> Episode:
    return Episode(
        episode_number=1,
        title="战神豪婿之归来重生",
        is_paywall=False,
        scenes=[
            Scene(
                scene_id="1-1",
                time="白天",
                location_type="室内",
                location="豪华办公室",
                characters=["叶枫", "林清月"],
                plots=[
                    Plot(type="action", content="叶枫推门而入，脸色阴沉。"),
                    Plot(type="dialogue", content="我们离婚吧。", character="叶枫"),
                    Plot(type="action", content="林清月抬头看向他，眼中满是疑惑。"),
                    Plot(type="dialogue", content="你说什么？", character="林清月", is_cliffhanger=False),
                ],
            )
        ],
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

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

class FormatValidator:
    """
    剧本格式校验器 (Format Validator)
    职责：根据红果短剧业务规范对生产出的单集内容进行逻辑与格式审查，
    包括：时长估算、付费点位置检查、黄金三集钩子检测、以及 JSON 结构完整性校验。
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

        # 2. 单集时长边界校验 (剧本质量核心指标)
        if total_duration < self.min_duration_sec:
            warnings.append(f"单集预估时长偏短: {total_duration} 秒。红果脚本通常需要 (最少 {self.min_duration_sec} 秒)，建议增加描述性情节或对话。")
            score -= self.scoring.get("duration_short_penalty", 10)
        elif total_duration > self.max_duration_sec:
            errors.append(f"单集预估时长超标: {total_duration} 秒。红果单集建议 (最高 {self.max_duration_sec} 秒)，过长可能会导致制作成本上升及节奏拖沓。")
            score -= self.scoring.get("duration_long_penalty", 30)

        # 3. 剧本钩子 (Hook) 检测
        if last_plot:
            has_hook_at_end = last_plot.is_cliffhanger
        
        if not has_hook_at_end:
            warnings.append("剧本结尾缺少钩子情节 (is_cliffhanger=False)，可能会降低观众的下一集留存率。")
            score -= self.scoring.get("no_hook_penalty", 15)

        # 4. 付费墙位置逻辑检查 (针对第 10-15 集以后的付费点)
        if episode.is_paywall:
            if not has_hook_at_end:
                errors.append("付费墙剧本必须包含强力结尾钩子 [卡点]，以刺激用户产生付费冲动和购买欲望。")
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


def run_self_test(config: Optional[dict] = None) -> ValidationReport:
    report = FormatValidator(config=config).validate(build_self_test_episode())

    print("\n" + "=" * 10 + " 剧本格式校验结果展示 " + "=" * 10)
    print(f"当前集数: 第 {report.episode_number} 集")
    print(f"校验状态: {'✅ 通过' if report.is_valid else '❌ 存在问题'}")
    print(f"质量评分: {report.format_score} 分")

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

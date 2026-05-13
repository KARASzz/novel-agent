import pytest
from core_engine.validator import FormatValidator
from core_engine.schemas import Episode, Scene, Plot


def test_validator_cliffhanger():
    validator = FormatValidator()

    # Case 1: 第 1 集结尾无销子（应失败）
    bad_ep = Episode(
        episode_number=1,
        title="Bad",
        is_paywall=False,
        scenes=[
            Scene(
                scene_id="1-1",
                time="日",
                location_type="内",
                location="A",
                characters=["A"],
                plots=[Plot(type="action", content="Wait...", is_cliffhanger=False)],
            )
        ],
    )
    report = validator.validate(bad_ep)
    assert not report.is_valid
    assert any("前三集" in err for err in report.errors)

    # Case 2: 有销子
    good_ep = Episode(
        episode_number=1,
        title="Good",
        is_paywall=False,
        scenes=[
            Scene(
                scene_id="1-1",
                time="日",
                location_type="内",
                location="A",
                characters=["A"],
                plots=[Plot(type="action", content="Boom!", is_cliffhanger=True)],
            )
        ],
    )
    report = validator.validate(good_ep)
    assert report.is_valid


def test_validator_duration():
    validator = FormatValidator(min_duration_sec=30, max_duration_sec=60)

    short_ep = Episode(
        episode_number=10,
        title="Short",
        is_paywall=False,
        scenes=[
            Scene(
                scene_id="1-1",
                time="日",
                location_type="内",
                location="A",
                characters=["A"],
                plots=[
                    Plot(
                        type="dialogue",
                        content="Hi",
                        character="A",
                        is_cliffhanger=True,
                    )
                ],
            )
        ],
    )
    report = validator.validate(short_ep)
    assert any("时长偏短" in warn for warn in report.warnings)

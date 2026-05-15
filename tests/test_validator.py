from core_engine.validator import FanqieChapterValidator


def test_fanqie_chapter_validator_passes_strong_chapter():
    text = (
        "第一章：旧站台的电话\n"
        "上一章留下的证据还在掌心发烫，林照刚踏进旧站台，就被债主的人堵在检票口。"
        "对方逼他交出名单，还当众夺走母亲留下的怀表。林照没有退，他反手把录音笔按开，"
        "让所有人都听见对方威胁孤儿院的证据。人群一下炸开，债主脸色铁青。"
        "林照终于把第一口恶气压回去，完成一次反击。可电话突然响起，屏幕上只有一句话："
        "真正的名单，在你父亲坟前。"
    )

    report = FanqieChapterValidator(min_words=80, max_words=1000).validate(
        text,
        chapter_index=1,
        chapter_title="第一章：旧站台的电话",
        expected_characters=["林照"],
        required_setting_terms=["旧站台"],
    )

    assert report.is_valid
    # 检查 checks 字典中的关键字段
    assert "conflict_signals" in report.checks
    assert "ending_hook" in report.checks
    # 冲突信号应该 > 0（文本中有"逼"、"夺"等词）
    assert report.checks["conflict_signals"] >= 1
    # 章尾钩子应该存在（文本以问号结尾）
    assert report.checks["ending_hook"] is True


def test_fanqie_chapter_validator_catches_ai_tone_and_missing_hook():
    text = (
        "第二章：解释\n"
        "总之，可以说，不难看出，主角在这个过程中获得了复杂的情绪。"
        "这是一种无法用语言形容的成长，某种意义上无疑非常重要。"
    )

    report = FanqieChapterValidator(min_words=20, max_words=1000, ai_tone_limit=1).validate(
        text,
        chapter_index=2,
        chapter_title="第二章：解释",
        previous_writeback="上一章留下了债务危机",
        expected_characters=["林照"],
        required_setting_terms=["旧站台"],
    )

    # AI腔超标（4 > 1限制）且缺少章尾钩子，应判定为无效
    assert not report.is_valid
    # 错误应包含 AI 腔相关问题或章尾钩子不足
    assert any("AI腔" in err or "章尾追读钩子不足" in err or "预期人物未显化" in err for err in report.errors)
    # 设定连续性警告（人物"林照"和设定词"旧站台"缺失）
    assert any("预期人物" in warn or "关键设定词" in warn for warn in report.warnings)
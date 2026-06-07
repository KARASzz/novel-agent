import json
import os
import zipfile

from core_engine.packager import ProjectPackager


def test_fanqie_packager_exports_novel_outputs(tmp_path):
    chapter_dir = tmp_path / "novel_outputs" / "p1" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "chapter.md").write_text("# 第一章\n正文", encoding="utf-8")
    (chapter_dir / "next_chapter_writeback.json").write_text(
        json.dumps({"source_chapter_index": 1}, ensure_ascii=False),
        encoding="utf-8",
    )
    (chapter_dir / "fanqie_quality_report.json").write_text(
        json.dumps({"score": 92}, ensure_ascii=False),
        encoding="utf-8",
    )

    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "webnovel_outline_template_v1.md").write_text("# 大纲", encoding="utf-8")
    (templates / "webnovel_setting_bible_template_v1.md").write_text("# 设定集", encoding="utf-8")

    zip_path = ProjectPackager(str(tmp_path)).create_fanqie_package(
        project_name="旧站台",
        genre="都市逆袭",
        author_name="测试作者",
    )

    assert os.path.basename(zip_path).endswith("_番茄小说存稿包_" + os.path.basename(zip_path).split("_")[-1])
    assert "番茄小说存稿包" in os.path.basename(zip_path)
    with zipfile.ZipFile(zip_path) as zipf:
        names = set(zipf.namelist())
        assert "00_打包清单/manifest.json" in names
        assert "01_项目设定包/webnovel_outline_template_v1.md" in names
        assert "01_项目设定包/webnovel_setting_bible_template_v1.md" in names
        assert "02_正文分章/chapter_001.md" in names
        assert "03_章节回写索引/next_chapter_writebacks.json" in names
        assert "04_质检报告/chapter_001_fanqie_quality_report.json" in names

        manifest = json.loads(zipf.read("00_打包清单/manifest.json").decode("utf-8"))
        assert manifest["package_type"] == "fanqie_novel_draft"
        assert manifest["chapter_count"] == 1


def test_fanqie_packager_can_package_specific_chapter_root(tmp_path):
    source_root = tmp_path / "novel_outputs" / "production_runs" / "sample" / "runs" / "run_1" / "chapters"
    chapter_dir = source_root / "sample_zerg_queen" / "chapter_001"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "chapter.md").write_text("# 第一章\n正文", encoding="utf-8")
    (chapter_dir / "next_chapter_writeback.json").write_text(
        json.dumps({"source_chapter_index": 1}, ensure_ascii=False),
        encoding="utf-8",
    )
    (chapter_dir / "fanqie_quality_report.json").write_text(
        json.dumps({"score": 91}, ensure_ascii=False),
        encoding="utf-8",
    )

    zip_path = ProjectPackager(str(tmp_path)).create_fanqie_package(
        project_name="虫族女皇",
        genre="诸天万界流",
        author_name="默认作者",
        source_root=str(source_root),
        package_dir=str(tmp_path / "novel_outputs" / "production_runs" / "sample" / "runs" / "run_1" / "package"),
    )

    with zipfile.ZipFile(zip_path) as zipf:
        names = set(zipf.namelist())
        assert "02_正文分章/chapter_001.md" in names
        manifest = json.loads(zipf.read("00_打包清单/manifest.json").decode("utf-8"))
        assert manifest["source"] == str(source_root)
        assert manifest["chapter_count"] == 1

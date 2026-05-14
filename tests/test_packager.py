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
    (templates / "pitch_template.md").write_text("# 项目设定", encoding="utf-8")

    zip_path = ProjectPackager(str(tmp_path)).create_fanqie_package(
        project_name="旧站台",
        genre="都市逆袭",
        author_name="测试作者",
    )

    assert os.path.basename(zip_path).endswith("_番茄小说存稿包_" + os.path.basename(zip_path).split("_")[-1])
    assert "红果短剧投稿包" not in os.path.basename(zip_path)
    with zipfile.ZipFile(zip_path) as zipf:
        names = set(zipf.namelist())
        assert "00_打包清单/manifest.json" in names
        assert "01_项目设定包/项目大纲与核心人物小传.md" in names
        assert "02_正文分章/chapter_001.md" in names
        assert "03_章节回写索引/next_chapter_writebacks.json" in names
        assert "04_质检报告/chapter_001_fanqie_quality_report.json" in names

        manifest = json.loads(zipf.read("00_打包清单/manifest.json").decode("utf-8"))
        assert manifest["package_type"] == "fanqie_novel_draft"
        assert manifest["chapter_count"] == 1


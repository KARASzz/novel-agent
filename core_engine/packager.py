import zipfile
import glob
import os
import json
from datetime import datetime

class ProjectPackager:
    """
    小说打包流水线 (Project Packager)
    作用：将章节正文、项目设定包、章节回写索引和质检报告整理为番茄小说投稿/存稿结构。
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        # 设置读取路径
        self.output_dir = os.path.join(self.workspace_root, "scripts_output")
        self.novel_output_dir = os.path.join(self.workspace_root, "novel_outputs")
        self.templates_dir = os.path.join(self.workspace_root, "templates")

    def create_submission_package(self, project_name: str, genre: str, author_name: str) -> str:
        """组装番茄小说投稿/存稿包。保留旧方法名以兼容 CLI 和批处理入口。"""
        return self.create_fanqie_package(project_name=project_name, genre=genre, author_name=author_name)

    def _chapter_files_from_novel_outputs(self) -> list[str]:
        pattern = os.path.join(self.novel_output_dir, "*", "chapter_*", "chapter.md")
        return sorted(glob.glob(pattern))

    def _legacy_chapter_files(self) -> list[str]:
        return sorted(glob.glob(os.path.join(self.output_dir, "*_成品剧本.txt")))

    @staticmethod
    def _read_text(path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _collect_writebacks(self) -> list[dict]:
        writebacks = []
        pattern = os.path.join(self.novel_output_dir, "*", "chapter_*", "next_chapter_writeback.json")
        for path in sorted(glob.glob(pattern)):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except Exception:
                payload = {"source": path, "error": "read_failed"}
            writebacks.append(payload)
        return writebacks

    def _collect_quality_reports(self) -> list[tuple[str, str]]:
        reports = []
        pattern = os.path.join(self.novel_output_dir, "*", "chapter_*", "fanqie_quality_report.json")
        for path in sorted(glob.glob(pattern)):
            reports.append((path, self._read_text(path)))
        return reports

    def create_fanqie_package(self, project_name: str, genre: str, author_name: str) -> str:
        """输出番茄小说投稿/存稿结构 ZIP。"""
        os.makedirs(self.output_dir, exist_ok=True)

        date_str = datetime.now().strftime("%Y%m%d")
        zip_name = f"【{genre}】{project_name}_{author_name}_番茄小说存稿包_{date_str}.zip"
        zip_path = os.path.join(self.output_dir, zip_name)

        chapter_files = self._chapter_files_from_novel_outputs()
        legacy_files = self._legacy_chapter_files()
        writebacks = self._collect_writebacks()
        quality_reports = self._collect_quality_reports()

        manifest = {
            "project_name": project_name,
            "genre": genre,
            "author_name": author_name,
            "package_type": "fanqie_novel_draft",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "chapter_count": len(chapter_files) or len(legacy_files),
            "source": "novel_outputs" if chapter_files else "scripts_output_legacy",
        }

        print("📦 [打包程序] 正在生成番茄小说投稿/存稿包...")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("00_打包清单/manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

            pitch_file = os.path.join(self.templates_dir, "pitch_template.md")
            if os.path.exists(pitch_file):
                zipf.write(pitch_file, arcname="01_项目设定包/项目大纲与核心人物小传.md")
            else:
                zipf.writestr(
                    "01_项目设定包/README.md",
                    "# 项目设定包\n\n未发现 templates/pitch_template.md，请在正式投稿前补齐项目设定、人物小传和世界观规则。\n",
                )

            if chapter_files:
                for file in chapter_files:
                    chapter_dir = os.path.basename(os.path.dirname(file))
                    zipf.write(file, arcname=f"02_正文分章/{chapter_dir}.md")
            else:
                for index, file in enumerate(legacy_files, start=1):
                    basename = os.path.splitext(os.path.basename(file))[0]
                    zipf.write(file, arcname=f"02_正文分章/chapter_{index:03d}_{basename}.txt")

            zipf.writestr(
                "03_章节回写索引/next_chapter_writebacks.json",
                json.dumps(writebacks, ensure_ascii=False, indent=2),
            )
            if quality_reports:
                for path, content in quality_reports:
                    chapter_dir = os.path.basename(os.path.dirname(path))
                    zipf.writestr(f"04_质检报告/{chapter_dir}_fanqie_quality_report.json", content)
            else:
                zipf.writestr("04_质检报告/README.md", "未发现 fanqie_quality_report.json。\n")

        if not chapter_files and not legacy_files:
             print("⚠️ [打包警告]: 未发现章节正文，已生成只含清单与占位说明的番茄小说存稿包。")

        print(f"✅ 成功生成【番茄小说投稿/存稿包】：\n-> 📦 {zip_path}")
        return zip_path

import zipfile
import glob
import os
from datetime import datetime

class ProjectPackager:
    """
    剧本打包流水线 (Project Packager)
    作用：完成整个工作流工业化管线的最后一公里——将生成的一地碎片（几十个 txt 和大纲小传），
    一键压制成满足平台官方（如红果邮箱或番茄助手 APP）命名要求的标准 ZIP 投稿压缩包。
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        # 设置读取路径
        self.output_dir = os.path.join(self.workspace_root, "scripts_output")
        self.templates_dir = os.path.join(self.workspace_root, "templates")

    def create_submission_package(self, project_name: str, genre: str, author_name: str) -> str:
        """组装投递专用的拉链包"""
        os.makedirs(self.output_dir, exist_ok=True)

        # 红果经典严苛的文件夹与压缩包命名法: [赛道-剧名-笔名/工作室名-日期].zip
        date_str = datetime.now().strftime("%Y%m%d")
        zip_name = f"【{genre}】{project_name}_{author_name}_红果短剧投稿包_{date_str}.zip"
        # 将成品投稿包直接存放在 scripts_output 目录中
        zip_path = os.path.join(self.output_dir, zip_name)
        
        script_added = False
        
        print("📦 [打包程序] 启动终极封装与平台投递件准备程序...")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            
            # 1. 强力装载红果过审的灵魂：核心大纲 Pitch
            pitch_file = os.path.join(self.templates_dir, "pitch_template.md")
            if os.path.exists(pitch_file):
                # 入包重命名，以显得正式
                zipf.write(pitch_file, arcname="01_项目大纲与核心人物小传_必看.md")
            else:
                print("⚠️ [打包警告]: 未在 templates 文件夹中发现立项大纲问卷 `pitch_template.md`，这极其影响过稿率。")
                
            # 2. 装载所有在 scripts_output 文件夹里躺好等待检阅的“完美渲染剧本”
            scripts_files = glob.glob(os.path.join(self.output_dir, "*_成品剧本.txt"))
            for index, file in enumerate(sorted(scripts_files)):
                basename = os.path.basename(file)
                # 使用一个专门的子文件夹在压缩包内通过存放，显得专业有序
                zipf.write(file, arcname=f"02_正文剧本存根库/{basename}")
                script_added = True
                
        if not script_added:
             print("⚠️ [打包警告]: `scripts_output/` 里空空如也，你打包了一个没放剧本的空气投递包..")
             
        print(f"✅ 成功生成【工业级投递压缩包】：\n-> 📦 {zip_path}")
        return zip_path

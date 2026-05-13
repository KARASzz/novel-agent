import json
import os
import math
from datetime import datetime

class FormatRenderer:
    """
    剧本格式渲染器 (FormatRenderer)
    目标: 将大模型吐出的 SceneData JSON 零配件强力拼装回工业格式的 txt 剧本。
    标准参考红果《玫瑰冠冕》排版规范：
    - 动作前必须加 ■
    - 旁白带 OS
    - 场次间必须空格
    """
    
    def __init__(self, character_speech_rate=4.5):
        # 语速设置：中文字/秒 (正常语速约每分钟180-250字)
        self.character_speech_rate = character_speech_rate

    def estimate_duration(self, plot) -> int:
        """
        基于内容预估单条情节的时长（秒）
        """
        content_len = len(plot.get("content", ""))
        plot_type = plot.get("type", "action")
        
        if plot_type in ["dialogue", "os", "monologue"]:
            # 台词或独白，根据字数算时长，算上语气停顿最小保守1秒
            seconds = math.ceil(content_len / self.character_speech_rate)
            return max(1, seconds)
        elif plot_type == "action":
            # 动作戏，估算一个经验值（字数/4 + 1秒）
            seconds = math.ceil(content_len / 4.0) + 1
            return max(2, seconds)
        return 1

    def render_episode(self, episode_data: dict) -> str:
        """
        全量渲染单集数据为工业标准格式文本
        """
        lines = []
        episode_number = episode_data.get("episode_number", 1)
        is_paywall = episode_data.get("is_paywall", False)
        
        total_duration_sec = 0
        total_word_count = 0
        
        # 逐场渲染
        scenes = episode_data.get("scenes", [])
        for scene in scenes:
            scene_id = scene.get("scene_id", f"{episode_number}-X")
            time = scene.get("time", "日")
            loc_type = scene.get("location_type", "内")
            location = scene.get("location", "未知地点")
            characters = scene.get("characters", [])
            plots = scene.get("plots", [])
            
            # --- 渲染场次索引行 ---
            lines.append(f"{scene_id} {time} {loc_type} {location}")
            
            # --- 渲染人物行 ---
            if characters:
                char_str = "、".join(characters)
                lines.append(f"人物：{char_str}")
                
            # --- 渲染情节 (动作 / 对白 / 旁白) ---
            scene_duration = 0
            for plot in plots:
                p_type = plot.get("type", "action")
                p_char = plot.get("character", "")
                content = plot.get("content", "")
                
                # 计算总字节数
                total_word_count += len(content)
                
                # 计算时长
                p_duration = plot.get("duration_sec")
                if not p_duration:
                    p_duration = self.estimate_duration(plot)
                scene_duration += p_duration
                
                # 按照规则拼装
                if p_type == "action":
                    # 动作前必须加 ■
                    lines.append(f"■{content}")
                elif p_type == "dialogue":
                    lines.append(f"{p_char}：{content}")
                elif p_type in ["monologue", "os", "OS"]:
                    lines.append(f"{p_char}OS：{content}")
                else:
                    lines.append(content)
            
            total_duration_sec += scene_duration
            
            # 每场结束后加空行换行
            lines.append("")
            
        # 移除集末多余的空行
        if lines and lines[-1] == "":
            lines.pop()
            
        # --- 如果是卡点集，打上付费卡点标签 ---
        if is_paywall:
            lines.append("")
            lines.append("[付费卡点]")
            
        # --- 拼装集末尾部统计数据 ---
        lines.append("")
        lines.append("=" * 30)
        lines.append(f"【单集统计】 第{episode_number}集")
        lines.append(f"预估时长：{total_duration_sec // 60}分{total_duration_sec % 60}秒 ({total_duration_sec}秒)")
        lines.append(f"纯文本字数：约 {total_word_count} 字")
        lines.append(f"场次总数：{len(scenes)} 场")
        lines.append("=" * 30)
        
        return "\n".join(lines)

    def process_file(self, input_json_path: str, output_txt_path: str):
        """
        读取 JSON 并输出单集的 txt
        """
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        result_text = self.render_episode(data)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_txt_path), exist_ok=True)
        
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(result_text)
            
        print(f"✅ 渲染成功: {output_txt_path}")


def build_self_test_episode_data() -> dict:
    return {
        "episode_number": 1,
        "title": "渲染自检样例",
        "is_paywall": False,
        "scenes": [
            {
                "scene_id": "1-1",
                "time": "日",
                "location_type": "内",
                "location": "办公室",
                "characters": ["林清月", "叶枫"],
                "plots": [
                    {"type": "action", "content": "林清月把合同拍在桌上，会议室瞬间安静。"},
                    {"type": "dialogue", "character": "林清月", "content": "今天这份方案，谁都别想糊弄过去。"},
                    {"type": "os", "character": "叶枫", "content": "她已经发现问题了，必须马上补救。"},
                ],
            }
        ],
    }


def run_self_test(output_dir: str | None = None) -> str:
    renderer = FormatRenderer()
    rendered_text = renderer.render_episode(build_self_test_episode_data())

    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = output_dir or os.path.join(workspace_root, "scripts_output", "diagnostics")
    os.makedirs(target_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_txt_path = os.path.join(target_dir, f"渲染引擎自检_{timestamp}.txt")
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write(rendered_text)

    print("✅ 渲染引擎自检完成。")
    print(f"📄 自检样例已输出: {output_txt_path}")
    return output_txt_path


if __name__ == "__main__":
    run_self_test()

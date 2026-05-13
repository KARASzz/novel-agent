import json
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

# ==========================================
# 1. 核心枚举定义 (Enums)
# ==========================================
# 使用内置的 Enum 来约束可能的规范取值。在利用 LLM 提取 JSON 时，可当作候选列表参考。

class PlotType(str, Enum):
    ACTION = "action"
    DIALOGUE = "dialogue"
    MONOLOGUE = "monologue"
    OS = "os"

class TimeOfDay(str, Enum):
    DAY = "日"
    NIGHT = "夜"
    MORNING = "晨"
    DUSK = "昏"

class LocationType(str, Enum):
    INDOOR = "内"
    OUTDOOR = "外"

class CliffhangerType(str, Enum):
    SUSPENSE = "悬念型"
    REVERSAL = "反转型"
    ESCALATION = "冲突升级型"
    EMOTION_LIMIT = "情绪临界型"

# ==========================================
# 2. 剧情结构层 (Plot, Scene, Episode)
# ==========================================

@dataclass
class Plot:
    """单个情节动作/对白/旁白"""
    type: str # 理论上应为 PlotType.value, 例如 "action", "dialogue", "os"
    content: str
    sequence: Optional[int] = None
    character: Optional[str] = None
    emotion: Optional[str] = None
    duration_sec: Optional[int] = None
    is_cliffhanger: bool = False
    intensity: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Plot":
        return cls(
            type=data.get("type", "action"),
            content=data.get("content", ""),
            sequence=data.get("sequence"),
            character=data.get("character"),
            emotion=data.get("emotion"),
            duration_sec=data.get("duration_sec"),
            is_cliffhanger=data.get("is_cliffhanger", False),
            intensity=data.get("intensity")
        )

@dataclass
class Scene:
    """单个场景数据"""
    scene_id: str
    time: str # "日", "夜", "晨", "昏"
    location_type: str # "内", "外"
    location: str
    characters: List[str]
    plots: List[Plot] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Scene":
        plots_data = data.get("plots", [])
        plots = [Plot.from_dict(p) for p in plots_data]
        return cls(
            scene_id=data.get("scene_id", ""),
            time=data.get("time", "日"),
            location_type=data.get("location_type", "内"),
            location=data.get("location", "未知"),
            characters=data.get("characters", []),
            plots=plots
        )

@dataclass
class Episode:
    """单集剧本数据，承载所有 Scene 的集合"""
    episode_number: int
    title: str
    is_paywall: bool = False
    core_conflict: Optional[str] = None
    hook: Optional[str] = None
    cliffhanger_type: Optional[str] = None
    estimated_duration_sec: Optional[int] = None
    scenes: List[Scene] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Episode":
        scenes_data = data.get("scenes", [])
        scenes = [Scene.from_dict(s) for s in scenes_data]
        return cls(
            episode_number=data.get("episode_number", 1),
            title=data.get("title", ""),
            is_paywall=data.get("is_paywall", False),
            core_conflict=data.get("core_conflict"),
            hook=data.get("hook"),
            cliffhanger_type=data.get("cliffhanger_type"),
            estimated_duration_sec=data.get("estimated_duration_sec"),
            scenes=scenes
        )

# ==========================================
# 3. 设定与架构层 (Premise, Character) - 选填或前置环节使用
# ==========================================

@dataclass
class CorePremise:
    """一句话短剧核心设定"""
    genre: str
    misunderstanding_type: str
    misunderstanding_desc: str
    audience_expectation: str
    logline: str
    target_episodes: int
    paywall_episode: int

@dataclass
class Character:
    """剧本人物小传"""
    name: str
    role: str # "protagonist", "antagonist", "supporting"
    age: int
    personality: str
    core_desire: str
    external_conflict: str
    internal_conflict: str
    arc: str
    catchphrase: str

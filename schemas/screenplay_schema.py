"""YAML Screenplay Schema - 工业级剧本数据结构"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class CharacterRole(str, Enum):
    PROTAGONIST = "protagonist"
    SUPPORTING = "supporting"
    ANTAGONIST = "antagonist"
    NPC = "npc"


class CameraShot(str, Enum):
    CLOSE_UP = "close_up"
    MEDIUM_SHOT = "medium_shot"
    WIDE_SHOT = "wide_shot"
    REACTION_SHOT = "reaction_shot"
    POV = "pov"
    TRACKING = "tracking"
    ESTABLISHING = "establishing"
    OVER_SHOULDER = "over_shoulder"
    TWO_SHOT = "two_shot"
    DUTCH_ANGLE = "dutch_angle"


class TimeOfDay(str, Enum):
    DAWN = "dawn"
    MORNING = "morning"
    DAY = "day"
    NOON = "noon"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    LATE_NIGHT = "late_night"


class SceneType(str, Enum):
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    INTERIOR_EXTERIOR = "int_ext"


# ---------- 角色 ----------

class CharacterRelationship(BaseModel):
    target_id: str
    relation: str
    description: str = ""


class Character(BaseModel):
    id: str = Field(..., description="格式 char_NNN，如 char_001")
    name: str
    gender: Gender
    age: Optional[int] = None
    role: CharacterRole
    personality: str = ""
    goal: str = ""
    background: str = ""
    relationships: list[CharacterRelationship] = []


# ---------- 场景 ----------

class SceneHeading(BaseModel):
    scene_type: SceneType = SceneType.INTERIOR
    location: str
    time: TimeOfDay = TimeOfDay.DAY
    description: str = ""


class DialogueLine(BaseModel):
    speaker: str = Field(..., description="Character ID (char_xxx)")
    content: str
    subtext: str = ""
    emotion: str = ""


class CameraNote(BaseModel):
    shot: CameraShot
    subject: str = ""
    description: str = ""


class Scene(BaseModel):
    id: str = Field(..., description="格式 scene_NNN，如 scene_001")
    chapter_ref: int = 1
    heading: SceneHeading
    participants: list[str] = []
    objective: str = ""
    summary: str = ""
    dialogue: list[DialogueLine] = []
    action_lines: list[str] = []
    camera_notes: list[CameraNote] = []
    duration_estimate: int = Field(default=60, description="Estimated seconds")


# ---------- 剧情节拍 ----------

class StoryBeat(BaseModel):
    id: str
    name: str
    description: str
    chapter_ref: int
    scene_refs: list[str] = []
    beat_type: str = ""  # inciting_incident, climax, resolution, turning_point
    emotional_tone: str = ""


# ---------- 评分 ----------

class ScoreBreakdown(BaseModel):
    structure: int = Field(ge=0, le=100)
    dialogue: int = Field(ge=0, le=100)
    pacing: int = Field(ge=0, le=100)
    character_consistency: int = Field(ge=0, le=100)
    overall: int = Field(ge=0, le=100)


# ---------- 元信息 ----------

class ScreenplayMetadata(BaseModel):
    generator: str = "AI Novel To Screenplay"
    version: str = "1.0.0"
    source_chapters: int = 3
    word_count: int = 0
    processing_time_ms: int = 0


# ---------- 完整剧本 ----------

class Screenplay(BaseModel):
    title: str
    genre: str = ""
    author: str = ""
    summary: str = ""
    metadata: ScreenplayMetadata = Field(default_factory=ScreenplayMetadata)
    characters: list[Character] = []
    story_beats: list[StoryBeat] = []
    scenes: list[Scene] = []
    score: Optional[ScoreBreakdown] = None
    consistency_report: Optional[dict] = None

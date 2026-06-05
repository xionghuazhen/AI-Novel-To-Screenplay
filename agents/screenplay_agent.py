"""剧本生成 Agent - 组装 YAML 剧本 + 质量评分 + 一致性检查"""
from backend.llm_provider import get_llm
from schemas.screenplay_schema import ScoreBreakdown

SYSTEM_PROMPT = """你是资深剧本编辑。为所有场景一次性生成镜头建议。

## 镜头类型
- close_up: 表现人物情感
- medium_shot: 对话场景
- wide_shot: 环境展示
- reaction_shot: 反应镜头
- establishing: 场景建立
- pov: 角色视角
- tracking: 跟拍动作
- over_shoulder: 过肩镜头
- two_shot: 双人镜头
- dutch_angle: 倾斜镜头

## 输出格式
严格输出 JSON 数组，每个元素包含 scene_id 和 camera_notes：
[
  {
    "scene_id": "scene_001",
    "camera_notes": [
      {"shot": "establishing", "subject": "青云宗全景", "description": "展示青云宗的宏伟建筑群"},
      {"shot": "medium_shot", "subject": "林凡与师父", "description": "两人对峙的中景"}
    ]
  }
]

## 规则
- 每个场景给 1-3 个镜头建议
- 必须为每个场景都生成镜头建议"""


def add_camera_notes(scenes: list[dict], characters: list[dict]) -> list[dict]:
    """为所有场景一次性添加镜头建议（批量调用）"""
    if not scenes:
        return scenes

    # 检查是否所有场景都已有镜头建议
    all_have_notes = all(s.get("camera_notes") for s in scenes)
    if all_have_notes:
        return scenes

    llm = get_llm()

    scenes_text_parts = []
    for scene in scenes:
        scenes_text_parts.append(
            f"--- {scene['id']} ---\n"
            f"地点：{scene['heading']['location']}\n"
            f"剧情目标：{scene.get('objective', '')}\n"
            f"动作：{scene.get('action_lines', [])}\n"
            f"对白数量：{len(scene.get('dialogue', []))} 句"
        )
    all_scenes_text = "\n\n".join(scenes_text_parts)

    response = llm.chat(
        user_message=all_scenes_text,
        system=SYSTEM_PROMPT,
        temperature=0.5,
        max_tokens=4096,
    )
    try:
        result = llm.extract_json(response)
        if isinstance(result, list):
            notes_map = {}
            for item in result:
                sid = item.get("scene_id", "")
                notes = item.get("camera_notes", [])
                if isinstance(notes, dict):
                    notes = [notes]
                notes_map[sid] = notes
            for scene in scenes:
                if scene["id"] in notes_map:
                    scene["camera_notes"] = notes_map[scene["id"]]
        elif isinstance(result, dict):
            for scene_id, notes in result.items():
                for s in scenes:
                    if s["id"] == scene_id:
                        s["camera_notes"] = notes if isinstance(notes, list) else [notes]
                        break
    except (ValueError, KeyError):
        pass

    for scene in scenes:
        if "camera_notes" not in scene:
            scene["camera_notes"] = []

    return scenes


def score_screenplay(screenplay_data: dict) -> ScoreBreakdown:
    """对剧本进行质量评分（基于规则，无 LLM 调用）"""
    chars = screenplay_data.get("characters", [])
    scenes = screenplay_data.get("scenes", [])

    structure = _score_structure(screenplay_data)
    dialogue = _score_dialogue(scenes)
    pacing = _score_pacing(scenes)
    char_consistency = _score_character_consistency(chars, scenes)

    overall = int((structure + dialogue + pacing + char_consistency) / 4)

    return ScoreBreakdown(
        structure=structure,
        dialogue=dialogue,
        pacing=pacing,
        character_consistency=char_consistency,
        overall=overall,
    )


def _score_structure(data: dict) -> int:
    scenes = data.get("scenes", [])
    beats = data.get("story_beats", [])
    score = 70
    if scenes:
        score += 10
    if beats:
        score += 10
    if len(scenes) >= 5:
        score += 5
    if data.get("summary"):
        score += 5
    return min(score, 100)


def _score_dialogue(scenes: list) -> int:
    if not scenes:
        return 0
    total_dialogue = sum(len(s.get("dialogue", [])) for s in scenes)
    if total_dialogue == 0:
        return 40
    score = 60 + min(total_dialogue, 20)
    return min(score, 100)


def _score_pacing(scenes: list) -> int:
    if not scenes:
        return 50
    durations = [s.get("duration_estimate", 60) for s in scenes]
    avg_duration = sum(durations) / len(durations) if durations else 0
    if 60 <= avg_duration <= 180:
        return 85
    return 70


def _score_character_consistency(characters: list, scenes: list) -> int:
    if not characters or not scenes:
        return 50
    char_ids = {c.get("id") for c in characters}
    scene_participants = set()
    for s in scenes:
        scene_participants.update(s.get("participants", []))
    unknown = scene_participants - char_ids
    if unknown:
        return max(50, 100 - len(unknown) * 10)
    return 85


def check_consistency(screenplay_data: dict) -> dict:
    """检查剧本一致性（纯规则，无 LLM 调用）"""
    chars = screenplay_data.get("characters", [])
    scenes = screenplay_data.get("scenes", [])
    char_ids = {c.get("id") for c in chars}
    issues = []

    for scene in scenes:
        for pid in scene.get("participants", []):
            if pid not in char_ids:
                issues.append(f"{scene['id']}: 引用了不存在的角色 {pid}")
        for d in scene.get("dialogue", []):
            if d.get("speaker") not in char_ids:
                issues.append(f"{scene['id']}: 对白引用了不存在的角色 {d.get('speaker')}")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "issue_count": len(issues),
    }

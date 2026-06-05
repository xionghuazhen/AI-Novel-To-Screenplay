"""对白生成 Agent - 将叙述文字转换为影视对白"""
from backend.llm_provider import get_llm

SYSTEM_PROMPT = """你是影视对白编剧。为所有场景一次性生成对白。

## 职责
1. 将角色的情感描述转换为符合性格的对白
2. 为每个场景中的角色生成自然流畅的对话
3. 添加潜台词（subtext）和情感标注
4. 保持对白风格与角色性格一致

## 输出格式
严格输出 JSON 数组，每个元素包含 scene_id 和对白：
[
  {
    "scene_id": "scene_001",
    "dialogue": [
      {
        "speaker": "char_001",
        "content": "师父，这些年你一直在骗我吗？",
        "subtext": "林凡内心已经知道真相，但仍希望师父亲口否认",
        "emotion": "愤怒中带着恳求"
      }
    ]
  }
]

## 规则
- speaker 必须使用已知角色 ID
- 对白要影视化、口语化，不要书面语
- 每句对白不超过 50 字
- 符合角色性格（参考 personality 字段）
- 禁止生成角色设定之外的对白
- 必须为每个场景都生成对白"""


def generate_dialogue(scenes: list[dict], characters: list[dict]) -> list[dict]:
    """为所有场景一次性生成对白（批量调用）"""
    if not scenes:
        return scenes

    llm = get_llm()
    char_info = {c.get("id", ""): c for c in characters}

    # 构建所有场景的摘要
    scenes_text_parts = []
    for scene in scenes:
        participants_info = []
        for pid in scene.get("participants", []):
            char = char_info.get(pid, {})
            participants_info.append(
                f"{pid} ({char.get('name', '?')}): {char.get('personality', '')}"
            )

        action_lines = "\n".join(scene.get("action_lines", [])[:5])
        scenes_text_parts.append(
            f"--- {scene['id']} ---\n"
            f"地点：{scene['heading']['location']}\n"
            f"时间：{scene['heading']['time']}\n"
            f"剧情目标：{scene.get('objective', scene.get('summary', ''))}\n"
            f"动作提示：\n{action_lines}\n"
            f"在场角色：\n" + "\n".join(participants_info)
        )

    all_scenes_text = "\n\n".join(scenes_text_parts)

    response = llm.chat(
        user_message=all_scenes_text,
        system=SYSTEM_PROMPT,
        temperature=0.7,
        max_tokens=8192,
    )
    try:
        result = llm.extract_json(response)
        if isinstance(result, dict):
            # {"scene_001": [...], ...} 格式
            for scene_id, dialogue in result.items():
                for s in scenes:
                    if s["id"] == scene_id:
                        s["dialogue"] = dialogue if isinstance(dialogue, list) else [dialogue]
                        break
        elif isinstance(result, list):
            # [{"scene_id": "...", "dialogue": [...]}, ...] 格式
            dialogue_map = {}
            for item in result:
                sid = item.get("scene_id", "")
                d = item.get("dialogue", [])
                if isinstance(d, dict):
                    d = [d]
                dialogue_map[sid] = d
            for scene in scenes:
                if scene["id"] in dialogue_map:
                    scene["dialogue"] = dialogue_map[scene["id"]]
    except (ValueError, KeyError):
        pass

    # 为没有生成对白的场景填充空数组
    for scene in scenes:
        if "dialogue" not in scene:
            scene["dialogue"] = []

    return scenes


def modify_dialogue(scenes: list[dict], modification_request: str, characters: list[dict]) -> list[dict]:
    """根据用户要求修改对白（多轮修改能力）"""
    llm = get_llm()
    response = llm.chat(
        user_message=(
            f"修改要求：{modification_request}\n\n"
            f"当前场景数据：\n{_scenes_to_text(scenes)}"
        ),
        system="你是剧本编辑。根据用户要求修改场景对白和动作描述。输出完整的修改后场景 JSON 数组。",
        temperature=0.5,
    )
    try:
        return llm.extract_json(response)
    except ValueError:
        return scenes


def _scenes_to_text(scenes: list[dict]) -> str:
    """场景列表转可读文本"""
    lines = []
    for s in scenes:
        lines.append(f"\n{s['id']}: {s['heading']['location']} - {s.get('objective', '')}")
        for d in s.get("dialogue", []):
            lines.append(f"  {d['speaker']}: {d['content']}")
    return "\n".join(lines)

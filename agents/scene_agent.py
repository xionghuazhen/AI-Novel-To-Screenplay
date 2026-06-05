"""场景拆分 Agent - 将小说拆分为剧本场景"""
from backend.llm_provider import get_llm

SYSTEM_PROMPT = """你是影视场景拆分专家。将所有章节一次性拆分为可拍摄的场景。

## 职责
1. 识别场景切换点（地点变化、时间跳跃）
2. 为每个场景定义：时间、地点、类型、参与角色、剧情目标
3. 保持剧情连续性
4. 估算每个场景的时长

## 场景类型
- interior (INT.): 室内场景
- exterior (EXT.): 室外场景
- int_ext (INT./EXT.): 内外结合

## 时间
dawn, morning, noon, afternoon, evening, night, late_night

## 输出格式
严格输出 JSON 数组：
[
  {
    "chapter_ref": 1,
    "heading": {
      "scene_type": "interior",
      "location": "青云宗大殿",
      "time": "morning",
      "description": "晨光透过大殿的雕花木窗"
    },
    "participants": ["char_001", "char_002"],
    "objective": "林凡向师父质问真相",
    "summary": "林凡在大殿中与师父对峙，气氛紧张",
    "action_lines": ["林凡推门而入", "王海背对着他站在窗前"],
    "duration_estimate": 120
  }
]

## 规则
- participants 使用角色 ID (char_xxx)
- 必须保持剧情连续性
- 每章拆分 3-8 个场景
- 综合所有章节内容，一次性输出所有场景"""


def split_scenes(chapters: list[dict], characters: list[dict]) -> list[dict]:
    """将所有章节一次性拆分为场景（批量调用）"""
    llm = get_llm()
    char_id_map = {c.get("name", ""): c.get("id", "") for c in characters}

    chapter_texts = []
    for c in chapters:
        content = c["content"]
        if len(content) > 6000:
            content = content[:6000] + "\n...(后续内容省略)"
        chapter_texts.append(
            f"=== 第{c['index']}章 {c['title']} ===\n{content}"
        )
    all_content = "\n\n".join(chapter_texts)

    response = llm.chat(
        user_message=f"可用角色ID：{list(char_id_map.values())}\n\n小说内容：\n{all_content}",
        system=SYSTEM_PROMPT,
        temperature=0.4,
        max_tokens=8192,
    )
    try:
        scenes = llm.extract_json(response)
        if isinstance(scenes, dict):
            scenes = [scenes]
    except (ValueError, KeyError):
        return []

    # 重新编号
    for i, scene in enumerate(scenes):
        scene["id"] = f"scene_{i+1:03d}"

    return scenes

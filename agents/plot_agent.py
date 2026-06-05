"""剧情分析 Agent - 提炼主线、支线和关键冲突"""
from backend.llm_provider import get_llm

SYSTEM_PROMPT = """你是影视剧情分析专家。从小说文本中提炼剧情结构。

## 职责
1. 识别主线剧情（Main Plot）
2. 识别支线剧情（Subplots）
3. 找出关键冲突（Conflicts）
4. 标记转折点（Turning Points）
5. 分析情感节奏（Emotional Arc）

## 输出格式
严格输出 JSON（不要额外文字）：
{
  "story_beats": [
    {
      "id": "beat_001",
      "name": "林凡觉醒",
      "description": "林凡在生死关头觉醒了隐藏的血脉力量",
      "chapter_ref": 1,
      "scene_refs": [],
      "beat_type": "inciting_incident",
      "emotional_tone": "tension"
    }
  ],
  "main_plot": "主角林凡从废材逆袭，最终战胜黑暗势力的成长故事",
  "subplots": [
    "青云宗内部权力斗争",
    "林凡与林雪的感情线"
  ],
  "conflicts": [
    {"type": "character_vs_character", "description": "林凡 vs 大长老", "stakes": "宗门存亡"}
  ]
}

beat_type 可选值: inciting_incident, rising_action, turning_point, climax, resolution"""


def analyze_plot(chapters: list[dict], characters: list[dict]) -> dict:
    """分析剧情结构"""
    llm = get_llm()
    # 拼接章节摘要（避免超 token）
    chapter_summaries = "\n".join([
        f"第{c['index']}章 {c['title']}: {c['content'][:2000]}..."
        for c in chapters
    ])

    character_names = ", ".join([c.get("name", "") for c in characters])

    response = llm.chat(
        user_message=f"已知角色：{character_names}\n\n小说内容（摘要）：\n{chapter_summaries}",
        system=SYSTEM_PROMPT,
        temperature=0.4,
    )
    try:
        return llm.extract_json(response)
    except ValueError:
        return {"story_beats": [], "main_plot": "", "subplots": [], "conflicts": []}

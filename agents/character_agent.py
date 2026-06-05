"""角色提取 Agent - 从小说中提取所有人物信息"""
from backend.llm_provider import get_llm

SYSTEM_PROMPT = """你是影视角色分析专家。从小说文本中提取所有人物信息。

## 职责
1. 识别所有有名字或对话的角色
2. 判断角色定位：protagonist（主角）、supporting（配角）、antagonist（反派）、npc（龙套）
3. 推断人物性格、目标、背景故事
4. 识别人物之间的关系

## 输出格式
严格输出 JSON 数组（不要额外文字）：
[
  {
    "id": "char_001",
    "name": "林凡",
    "gender": "male",
    "age": 18,
    "role": "protagonist",
    "personality": "坚毅果敢，重情重义",
    "goal": "为师父报仇，重振青云宗",
    "background": "孤儿出身，被师父收养",
    "relationships": [
      {"target_id": "char_002", "relation": "师徒", "description": "师父王海"}
    ]
  }
]

## 规则
- id 格式: char_001, char_002, ...
- role 必须是: protagonist, supporting, antagonist, npc 之一
- 禁止编造不存在的角色
- gender 必须是: male, female, other
- 如果信息不足，对应字段留空字符串
- 综合所有章节内容，一次性输出所有角色（去重）"""


def extract_characters(chapters: list[dict]) -> list[dict]:
    """从多个章节中一次性提取所有角色（批量调用）"""
    llm = get_llm()

    chapter_texts = []
    for c in chapters:
        chapter_texts.append(f"=== {c['title']} ===\n{c['content'][:6000]}")
    all_content = "\n\n".join(chapter_texts)

    response = llm.chat(
        user_message=all_content,
        system=SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=4096,
    )
    try:
        chars = llm.extract_json(response)
        if isinstance(chars, dict):
            chars = [chars]
        return chars
    except (ValueError, KeyError):
        return []

"""小说章节解析 Agent - 自动识别章节并分片"""
import re
from backend.llm_provider import get_llm

SYSTEM_PROMPT = """你是小说结构分析专家。你的任务是从给定的小说文本中识别并拆分章节。

## 职责
1. 识别章节标题和边界（支持多种格式："第X章"、"Chapter X"、"X."、"卷X"等）
2. 将每个章节的完整内容提取出来
3. 统计每章字数

## 输出格式
严格按以下 JSON 格式输出（不要额外文字）：
{
  "chapters": [
    {"index": 1, "title": "第一章 重生", "word_count": 3500, "content": "完整章节内容..."},
    {"index": 2, "title": "第二章 修炼", "word_count": 4100, "content": "完整章节内容..."}
  ],
  "total_chapters": 2,
  "total_words": 7600
}

## 规则
- 如果文本没有明确章节标记，按每 3000-5000 字自动分段
- 保留原文的段落结构
- content 字段包含该章节的全部原始文本"""


def parse_chapters(novel_text: str) -> dict:
    """解析小说文本，识别并拆分章节"""
    # 先尝试用正则识别章节标记（支持中文数字、阿拉伯数字、多种格式）
    chapter_patterns = [
        r"(第[零一二三四五六七八九十百千\d]+章[^\n]*)",
        r"(Chapter\s+\d+[^\n]*)",
        r"(第[零一二三四五六七八九十百千\d]+节[^\n]*)",
        r"(卷[零一二三四五六七八九十百千\d]+[^\n]*)",
        r"(^[零一二三四五六七八九十百千\d]+[\.、]\s*[^\n]*)",
    ]

    for pattern in chapter_patterns:
        matches = list(re.finditer(pattern, novel_text, re.MULTILINE))
        if len(matches) >= 3:
            return _split_by_markers(novel_text, matches)

    # 没有足够章节标记，按字数自动分段
    return _auto_split(novel_text)


def _split_by_markers(text: str, markers: list) -> dict:
    """根据章节标记拆分"""
    chapters = []
    for i, match in enumerate(markers):
        title = match.group(1).strip()
        start = match.start()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        content = text[start:end].strip()

        chapters.append({
            "index": i + 1,
            "title": title,
            "word_count": len(content),
            "content": content,
        })

    return {
        "chapters": chapters,
        "total_chapters": len(chapters),
        "total_words": sum(c["word_count"] for c in chapters),
    }


def _auto_split(text: str, chunk_size: int = 4000) -> dict:
    """按字数自动分段"""
    paragraphs = text.split("\n\n")
    chapters = []
    current_chunk = ""
    chunk_index = 1

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chapters.append({
                "index": chunk_index,
                "title": f"第{chunk_index}段",
                "word_count": len(current_chunk),
                "content": current_chunk.strip(),
            })
            chunk_index += 1
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chapters.append({
            "index": chunk_index,
            "title": f"第{chunk_index}段",
            "word_count": len(current_chunk),
            "content": current_chunk.strip(),
        })

    return {
        "chapters": chapters,
        "total_chapters": len(chapters),
        "total_words": sum(c["word_count"] for c in chapters),
    }


def parse_with_llm(novel_text: str) -> dict:
    """使用 LLM 辅助解析（用于格式不规范的文本）"""
    llm = get_llm()
    # 截断过长的输入
    text_sample = novel_text[:12000] if len(novel_text) > 12000 else novel_text
    response = llm.chat(
        user_message=f"请分析以下小说文本，识别章节结构：\n\n{text_sample}",
        system=SYSTEM_PROMPT,
        temperature=0.3,
    )
    return llm.extract_json(response)

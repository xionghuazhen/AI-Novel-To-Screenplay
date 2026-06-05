"""LangGraph 工作流 - 编排 6 个 Agent 的流水线（批量优化 + RAG 记忆）"""
from __future__ import annotations
import hashlib
import re
import time
from typing import TypedDict
from langgraph.graph import StateGraph, END
from agents.parser import parse_chapters
from agents.character_agent import extract_characters
from agents.plot_agent import analyze_plot
from agents.scene_agent import split_scenes
from agents.dialogue_agent import generate_dialogue
from agents.screenplay_agent import add_camera_notes, score_screenplay, check_consistency
from agents.rag_memory import get_memory


def normalize_ids(data: dict) -> dict:
    chars = data.get("characters", [])
    scenes = data.get("scenes", [])

    old_char_ids: dict[str, str] = {}
    for i, c in enumerate(chars):
        new_id = f"char_{i+1:03d}"
        old_char_ids[c.get("id", "")] = new_id
        c["id"] = new_id
        for rel in c.get("relationships", []):
            old_tid = rel.get("target_id", "")
            if old_tid:
                rel["target_id"] = old_char_ids.get(old_tid, old_tid)

    old_scene_ids: dict[str, str] = {}
    for i, s in enumerate(scenes):
        new_id = f"scene_{i+1:03d}"
        old_scene_ids[s.get("id", "")] = new_id
        s["id"] = new_id
        s["participants"] = [old_char_ids.get(p, p) for p in s.get("participants", [])]
        for d in s.get("dialogue", []):
            old_spk = d.get("speaker", "")
            if old_spk:
                d["speaker"] = old_char_ids.get(old_spk, old_spk)

    for beat in data.get("story_beats", []):
        beat["scene_refs"] = [old_scene_ids.get(r, r) for r in beat.get("scene_refs", [])]

    return data


class WorkflowState(TypedDict):
    novel_text: str
    chapters: list[dict]
    characters: list[dict]
    plot_data: dict
    scenes: list[dict]
    screenplay_data: dict
    errors: list[str]
    rag_context: str


def node_parse(state: WorkflowState) -> WorkflowState:
    """节点1: 小说解析（纯规则，无 LLM 调用）"""
    t0 = time.time()
    try:
        result = parse_chapters(state["novel_text"])
        state["chapters"] = result["chapters"]
        print(f"[1/6] 章节解析完成: {len(state['chapters'])} 章, {int((time.time()-t0)*1000)}ms")
    except Exception as e:
        state["errors"].append(f"Parse error: {e}")
        state["chapters"] = []
    return state


def node_extract_characters(state: WorkflowState) -> WorkflowState:
    """节点2: 角色提取（1 次批量 LLM 调用，含 RAG 记忆）"""
    t0 = time.time()
    try:
        # 注入 RAG 记忆上下文
        chapters = state["chapters"]
        if state.get("rag_context"):
            # 将记忆上下文附加到第一个章节的内容中
            chapters = [dict(c) for c in chapters]
            chapters[0] = dict(chapters[0])
            chapters[0]["content"] = (
                f"[已有记忆]\n{state['rag_context']}\n\n"
                f"{chapters[0]['content']}"
            )
        state["characters"] = extract_characters(chapters)
        print(f"[2/6] 角色提取完成: {len(state['characters'])} 个角色, {int((time.time()-t0)*1000)}ms")
    except Exception as e:
        state["errors"].append(f"Character extraction error: {e}")
        state["characters"] = []
    return state


def node_analyze_plot(state: WorkflowState) -> WorkflowState:
    """节点3: 剧情分析（1 次 LLM 调用）"""
    t0 = time.time()
    try:
        state["plot_data"] = analyze_plot(state["chapters"], state["characters"])
        print(f"[3/6] 剧情分析完成, {int((time.time()-t0)*1000)}ms")
    except Exception as e:
        state["errors"].append(f"Plot analysis error: {e}")
        state["plot_data"] = {}
    return state


def node_split_scenes(state: WorkflowState) -> WorkflowState:
    """节点4: 场景拆分（1 次批量 LLM 调用）"""
    t0 = time.time()
    try:
        state["scenes"] = split_scenes(state["chapters"], state["characters"])
        print(f"[4/6] 场景拆分完成: {len(state['scenes'])} 个场景, {int((time.time()-t0)*1000)}ms")
    except Exception as e:
        state["errors"].append(f"Scene split error: {e}")
        state["scenes"] = []
    return state


def node_generate_dialogue(state: WorkflowState) -> WorkflowState:
    """节点5: 对白生成（1 次批量 LLM 调用）"""
    t0 = time.time()
    try:
        state["scenes"] = generate_dialogue(state["scenes"], state["characters"])
        total_lines = sum(len(s.get("dialogue", [])) for s in state["scenes"])
        print(f"[5/6] 对白生成完成: {total_lines} 句, {int((time.time()-t0)*1000)}ms")
    except Exception as e:
        state["errors"].append(f"Dialogue generation error: {e}")
    return state


def node_assemble_screenplay(state: WorkflowState) -> WorkflowState:
    """节点6: 剧本组装 + 镜头建议（1 次批量 LLM 调用）+ 评分 + 一致性检查"""
    # 从第一个章节标题中提取书名
    first_title = state["chapters"][0]["title"] if state["chapters"] else ""
    _m = re.search(r'第[^章]+章\s*(.+)', first_title)
    title = _m.group(1).strip() if _m else (first_title.strip() or "未命名剧本")

    screenplay = {
        "title": title,
        "genre": "fantasy",
        "summary": state["plot_data"].get("main_plot", ""),
        "characters": state["characters"],
        "story_beats": state["plot_data"].get("story_beats", []),
        "scenes": state["scenes"],
    }

    t0 = time.time()
    try:
        state["scenes"] = add_camera_notes(state["scenes"], state["characters"])
        screenplay["scenes"] = state["scenes"]
        total_notes = sum(len(s.get("camera_notes", [])) for s in state["scenes"])
        print(f"[6/6] 镜头建议完成: {total_notes} 条, {int((time.time()-t0)*1000)}ms")
    except Exception as e:
        state["errors"].append(f"Camera notes error: {e}")

    try:
        screenplay["score"] = score_screenplay(screenplay).model_dump()
    except Exception as e:
        state["errors"].append(f"Score error: {e}")

    try:
        screenplay["consistency_report"] = check_consistency(screenplay)
    except Exception as e:
        state["errors"].append(f"Consistency check error: {e}")

    state["screenplay_data"] = screenplay
    return state


def build_workflow() -> StateGraph:
    workflow = StateGraph(WorkflowState)

    workflow.add_node("parse", node_parse)
    workflow.add_node("extract_characters", node_extract_characters)
    workflow.add_node("analyze_plot", node_analyze_plot)
    workflow.add_node("split_scenes", node_split_scenes)
    workflow.add_node("generate_dialogue", node_generate_dialogue)
    workflow.add_node("assemble_screenplay", node_assemble_screenplay)

    workflow.set_entry_point("parse")
    workflow.add_edge("parse", "extract_characters")
    workflow.add_edge("extract_characters", "analyze_plot")
    workflow.add_edge("analyze_plot", "split_scenes")
    workflow.add_edge("split_scenes", "generate_dialogue")
    workflow.add_edge("generate_dialogue", "assemble_screenplay")
    workflow.add_edge("assemble_screenplay", END)

    return workflow.compile()


def run_workflow(novel_text: str) -> dict:
    """运行完整的 Agent 流水线（共 ~5 次 LLM 调用 + RAG 记忆）"""
    print(f"\n{'='*50}\n开始处理小说, 共 {len(novel_text)} 字符\n{'='*50}")
    t_total = time.time()

    # 加载 RAG 记忆
    novel_hash = hashlib.md5(novel_text[:200].encode()).hexdigest()[:12]
    memory = get_memory(novel_hash)
    rag_context = memory.recall_context()
    if rag_context:
        print(f"[RAG] 加载记忆: {len(memory.data['characters'])} 个角色, {len(memory.data['scenes'])} 个场景")

    app = build_workflow()
    initial_state: WorkflowState = {
        "novel_text": novel_text,
        "chapters": [],
        "characters": [],
        "plot_data": {},
        "scenes": [],
        "screenplay_data": {},
        "errors": [],
        "rag_context": rag_context,
    }
    result = app.invoke(initial_state)
    data = result["screenplay_data"]
    if data:
        data = normalize_ids(data)
        # 保存到 RAG 记忆
        memory.extract_and_remember(data)
        print(f"[RAG] 记忆已更新 (版本 {memory.data['version']})")

    elapsed = int((time.time() - t_total) * 1000)
    print(f"{'='*50}\n处理完成, 总耗时: {elapsed}ms ({elapsed/1000:.1f}s)\n{'='*50}")
    if result.get("errors"):
        print(f"警告: {result['errors']}")
    return data

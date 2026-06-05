"""RAG 记忆机制 - 跨会话持久化角色和场景信息"""
from __future__ import annotations
import json
import os
from pathlib import Path

MEMORY_DIR = Path(__file__).parent.parent / ".memory"


class NovelMemory:
    """小说记忆管理 - 基于文件持久化的 RAG 记忆"""

    def __init__(self, novel_hash: str = "default"):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.memory_file = MEMORY_DIR / f"{novel_hash}.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.memory_file.exists():
            try:
                return json.loads(self.memory_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "characters": {},
            "scenes": {},
            "world_rules": [],
            "style_notes": [],
            "version": 1,
        }

    def save(self):
        self.memory_file.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def remember_character(self, char_id: str, info: dict):
        """记住角色信息，增量合并"""
        if char_id not in self.data["characters"]:
            self.data["characters"][char_id] = info
        else:
            existing = self.data["characters"][char_id]
            for key, value in info.items():
                if key == "relationships":
                    existing_rels = {r["target_id"] for r in existing.get("relationships", [])}
                    for rel in value:
                        if rel["target_id"] not in existing_rels:
                            existing.setdefault("relationships", []).append(rel)
                elif value and not existing.get(key):
                    existing[key] = value
        self.data["version"] += 1
        self.save()

    def remember_scene(self, scene_id: str, info: dict):
        """记住场景信息"""
        self.data["scenes"][scene_id] = info
        self.data["version"] += 1
        self.save()

    def add_world_rule(self, rule: str):
        """添加世界观规则"""
        if rule not in self.data["world_rules"]:
            self.data["world_rules"].append(rule)
            self.data["version"] += 1
            self.save()

    def add_style_note(self, note: str):
        """添加风格笔记"""
        if note not in self.data["style_notes"]:
            self.data["style_notes"].append(note)
            self.data["version"] += 1
            self.save()

    def recall_characters(self) -> list[dict]:
        """召回所有角色记忆"""
        return list(self.data["characters"].values())

    def recall_scenes(self) -> list[dict]:
        """召回所有场景记忆"""
        return list(self.data["scenes"].values())

    def recall_context(self) -> str:
        """生成可注入 LLM prompt 的上下文摘要"""
        parts = []

        chars = self.data["characters"]
        if chars:
            parts.append("## 已记忆角色")
            for cid, info in chars.items():
                parts.append(f"- {cid} {info.get('name', '?')}: {info.get('personality', '')}")

        rules = self.data["world_rules"]
        if rules:
            parts.append("\n## 世界观规则")
            for r in rules:
                parts.append(f"- {r}")

        notes = self.data["style_notes"]
        if notes:
            parts.append("\n## 风格笔记")
            for n in notes:
                parts.append(f"- {n}")

        return "\n".join(parts) if parts else ""

    def extract_and_remember(self, screenplay_data: dict):
        """从剧本数据中自动提取并记忆关键信息"""
        for char in screenplay_data.get("characters", []):
            self.remember_character(char.get("id", ""), {
                "name": char.get("name", ""),
                "role": char.get("role", ""),
                "personality": char.get("personality", ""),
                "goal": char.get("goal", ""),
                "relationships": char.get("relationships", []),
            })

        for scene in screenplay_data.get("scenes", []):
            self.remember_scene(scene.get("id", ""), {
                "location": scene.get("heading", {}).get("location", ""),
                "objective": scene.get("objective", ""),
                "participants": scene.get("participants", []),
            })

    def clear(self):
        """清除记忆"""
        self.data = {"characters": {}, "scenes": {}, "world_rules": [], "style_notes": [], "version": 1}
        self.save()


def get_memory(novel_hash: str = "default") -> NovelMemory:
    """获取小说记忆实例"""
    return NovelMemory(novel_hash)

from pathlib import Path
import re
import os

try:
    from skill_engine.base import SkillTool
except Exception:
    class SkillTool:
        name = ""
        description = ""
        def run(self, params):
            raise NotImplementedError


class MetaInterpreterTool(SkillTool):
    name = "meta_interpreter"
    description = "Reads meta-skill markdown files and generates a plan + decomposition."

    SEARCH_PATHS = [
        Path("meta"),
        Path("skills"),
        Path("data"),
        Path("/mnt/data")
    ]

    def _find_md_files(self):
        md_files = []
        for folder in self.SEARCH_PATHS:
            if folder.exists():
                md_files.extend(folder.glob("*.md"))
        return md_files

    def _parse_md(self, filepath: Path):
        text = filepath.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        headings = []
        bullets = []
        steps = []

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("#"):
                headings.append(stripped.lstrip("# ").strip())

            elif re.match(r"^\d+\.\s+", stripped):
                steps.append(re.sub(r"^\d+\.\s+", "", stripped))

            elif re.match(r"[-*+]\s+", stripped):
                bullets.append(re.sub(r"[-*+]\s+", "", stripped))

        return {
            "path": str(filepath),
            "raw": text,
            "headings": headings,
            "bullets": bullets,
            "steps": steps
        }

    def _score(self, task_words, text):
        text_words = re.findall(r"\w+", text.lower())
        if not text_words:
            return 0.0

        overlap = sum(1 for w in task_words if w in text_words)
        return overlap / len(set(text_words))

    def run(self, params):
        task = params.get("task") or params.get("query")
        if not task:
            return {"error": "Missing 'task' parameter"}

        task_words = re.findall(r"\w+", task.lower())
        md_files = self._find_md_files()

        parsed = []
        for f in md_files:
            info = self._parse_md(f)
            s = self._score(task_words, info["raw"])
            parsed.append({
                "path": info["path"],
                "score": s,
                "concepts": info["headings"][:5] + info["bullets"][:5],
            })

        parsed_sorted = sorted(parsed, key=lambda x: x["score"], reverse=True)[:8]

        all_concepts = []
        for doc in parsed_sorted:
            for c in doc["concepts"]:
                if c not in all_concepts:
                    all_concepts.append(c)

        decomposition = [
            f"Analyze concept: {c}" for c in all_concepts[:5]
        ]

        plan = [
            f"Goal: {task}",
            "1. Review top relevant meta documents.",
            "2. Extract important concepts.",
            "3. Generate reasoning steps from concepts.",
            "4. Assemble a structured plan.",
            "5. Validate results."
        ]

        return {
            "task": task,
            "decomposition": decomposition,
            "plan": plan,
            "used_files": parsed_sorted,
            "confidence": 0.8
        }


tool = MetaInterpreterTool()

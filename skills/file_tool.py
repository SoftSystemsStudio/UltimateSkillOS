import os
from typing import Optional, Dict, Any
from skill_engine.base import BaseSkill


from pydantic import BaseModel
from skill_engine.domain import SkillInput, SkillOutput

class FileToolInput(BaseModel):
    action: str
    path: str
    content: str = ""

class FileToolOutput(BaseModel):
    status: str = ""
    path: str = ""
    content: str = ""
    directory: str = ""
    items: list = []
    error: str = ""

class FileTool(BaseSkill):
    name = "file"
    version = "1.0.0"
    description = "Reads, writes, and manages files on the filesystem."
    input_schema = FileToolInput
    output_schema = FileToolOutput
    sla = None

    def _normalize_path(self, raw: Optional[str]) -> Optional[str]:
        if raw is None:
            return None
        if not isinstance(raw, str):
            return None
        cleaned = raw.strip()
        if cleaned == "":
            return None
        return cleaned

    def invoke(self, input_data: SkillInput, context) -> SkillOutput:
        params = input_data.payload
        action = params.get("action")
        raw_path = params.get("path")
        content = params.get("content", "")
        path = self._normalize_path(raw_path)
        if path is None:
            return {"error": "Invalid or missing file path"}
        if action == "read":
            if not os.path.exists(path):
                return {"error": f"File not found: {path}"}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data: str = f.read()
                return {"path": path, "content": data}
            except Exception as e:
                return {"error": str(e)}
        if action == "write":
            try:
                dir_path = os.path.dirname(path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"status": "written", "path": path}
            except Exception as e:
                return {"error": str(e)}
        if action == "append":
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(content)
                return {"status": "appended", "path": path}
            except Exception as e:
                return {"error": str(e)}
        if action == "list":
            if not os.path.isdir(path):
                return {"error": f"Not a directory: {path}"}
            try:
                items = os.listdir(path)
                return {"directory": path, "items": items}
            except Exception as e:
                return {"error": str(e)}
        return {"error": f"Unknown action: {action}"}

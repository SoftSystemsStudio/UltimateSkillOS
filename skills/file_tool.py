import os
from typing import Optional, Dict, Any
from skill_engine.base import BaseSkill


class FileTool(BaseSkill):
    name = "file"

    def _normalize_path(self, raw: Optional[str]) -> Optional[str]:
        """Ensure path is a valid string for type checking."""
        if raw is None:
            return None
        if not isinstance(raw, str):
            return None
        cleaned = raw.strip()
        if cleaned == "":
            return None
        return cleaned

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action")
        raw_path = params.get("path")
        content = params.get("content", "")

        # Type-safe path normalization
        path = self._normalize_path(raw_path)
        if path is None:
            return {"error": "Invalid or missing file path"}

        # ---- READ FILE ----
        if action == "read":
            if not os.path.exists(path):
                return {"error": f"File not found: {path}"}

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data: str = f.read()
                return {"path": path, "content": data}
            except Exception as e:
                return {"error": str(e)}

        # ---- WRITE FILE ----
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

        # ---- APPEND FILE ----
        if action == "append":
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(content)
                return {"status": "appended", "path": path}
            except Exception as e:
                return {"error": str(e)}

        # ---- LIST DIRECTORY ----
        if action == "list":
            if not os.path.isdir(path):
                return {"error": f"Not a directory: {path}"}

            try:
                items = os.listdir(path)
                return {"directory": path, "items": items}
            except Exception as e:
                return {"error": str(e)}

        return {"error": f"Unknown action: {action}"}

from skill_engine.base import SkillTool
import os
import json

class FileTool(SkillTool):
    name = "file"
    description = "Read and write files within the project workspace."

    def run(self, params):
        action = params.get("action")
        path = params.get("path")

        if not action:
            return {"error": "Missing 'action' parameter"}
        if not path:
            return {"error": "Missing 'path' parameter"}

        # Normalize path inside workspace
        base_dir = os.getcwd()
        full_path = os.path.join(base_dir, path)

        # Ensure directory exists for write operations
        if action in ("write", "append"):
            parent_dir = os.path.dirname(full_path)
            os.makedirs(parent_dir, exist_ok=True)

        # === ACTIONS ===

        # READ FILE
        if action == "read":
            if not os.path.exists(full_path):
                return {"error": f"File not found: {path}"}
            with open(full_path, "r", encoding="utf-8") as f:
                return {"content": f.read(), "path": path}

        # WRITE (overwrite)
        if action == "write":
            content = params.get("content", "")
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "written", "path": path}

        # APPEND
        if action == "append":
            content = params.get("content", "")
            with open(full_path, "a", encoding="utf-8") as f:
                f.write(content)
            return {"status": "appended", "path": path}

        # LIST DIRECTORY
        if action == "list":
            if not os.path.isdir(full_path):
                return {"error": f"Directory not found: {path}"}
            return {"directory": path, "items": os.listdir(full_path)}

        return {"error": f"Unknown action '{action}'"}

# Required for SkillEngine auto-loading
tool = FileTool()

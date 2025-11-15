import json
import sys
from skill_engine.engine import SkillEngine

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 -m skill_engine.cli <tool> '<json-input>'")
        sys.exit(1)

    tool = sys.argv[1]
    params = json.loads(sys.argv[2])

    engine = SkillEngine()
    result = engine.run(tool, params)
    print(json.dumps(result, indent=2))

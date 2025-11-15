# cli.py
from core.loader import SkillLoader
from core.router import Router
from skill_engine.engine import SkillEngine

def main():
    loader = SkillLoader()
    router = Router(loader)
    engine = SkillEngine(loader, router)

    print("UltimateSkillOS CLI loaded (no skills registered).")

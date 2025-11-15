#!/usr/bin/env python3
"""
core/loader.py
Reads all .md files in ../skills and writes a minimal data/skills.json
Fields: id, title, description, path
This is a simple loader used by the CLI; replace or extend with embeddings later.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / "skills"
OUT = ROOT / "data" / "skills.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

def simple_extract(md_text):
    lines = md_text.strip().splitlines()
    title = lines[0].lstrip('#').strip() if lines else "untitled"
    # first non-empty paragraph after header
    para = ""
    for line in lines[1:]:
        if line.strip():
            para = re.sub(r'\s+', ' ', line.strip())
            break
    return title, para

def load_skills():
    skills = []
    for p in sorted(SKILLS_DIR.glob("*.md")):
        txt = p.read_text(encoding='utf-8')
        title, desc = simple_extract(txt)
        skills.append({
            "id": p.name,
            "title": title,
            "description": desc,
            "path": str(p.resolve())
        })
    return skills

def main():
    skills = load_skills()
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(skills, f, indent=2)
    print(f"Wrote {len(skills)} skills to {OUT}")

if __name__ == "__main__":
    main()

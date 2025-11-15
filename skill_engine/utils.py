"""
skill_engine.utils
Small helpers used by skills and engine.
"""
import re

def clean_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    # basic normalization: collapse whitespace, trim
    s = re.sub(r'\s+', ' ', s).strip()
    return s

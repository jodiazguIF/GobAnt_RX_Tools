import re
from typing import Optional

RAD_RE_TEXT_HEAD = re.compile(r"^\s*(\d{6,})\b", flags=re.MULTILINE)
RAD_RE_FILENAME = re.compile(r"(\d{6,})")

def extract_from_text(doc_text: str) -> Optional[str]:
    head = "\n".join(doc_text.splitlines()[:3])
    m = RAD_RE_TEXT_HEAD.search(head)
    return m.group(1) if m else None

def extract_from_filename(filename: str) -> Optional[str]:
    m = RAD_RE_FILENAME.search(filename)
    return m.group(1) if m else None

def resolve(doc_text: str, filename: str) -> Optional[str]:
    return extract_from_filename(filename)
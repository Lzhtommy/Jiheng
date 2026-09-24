from __future__ import annotations

from ..paths import PLAYBOOKS_DIR


def load_playbook(filename: str) -> str:
    path = PLAYBOOKS_DIR / filename
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")

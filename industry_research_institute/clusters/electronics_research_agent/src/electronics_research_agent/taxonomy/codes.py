from __future__ import annotations


def normalize_code(code: str) -> str:
    s = (code or "").strip().upper()
    for suf in (".SZ", ".SH", ".BJ", ".SS", ".SI"):
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    if s.isdigit():
        return s.zfill(6)
    return s

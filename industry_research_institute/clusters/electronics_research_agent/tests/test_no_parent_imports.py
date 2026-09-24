from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

FORBIDDEN_MODS = {
    "valuation_router",
    "industry_data",
    "jobs",
    "api",
    "frontend_vue",
}
FORBIDDEN_TEXT = [
    re.compile(r"\bvaluation_router\b"),
    re.compile(r"\bindustry_data\b"),
    re.compile(r"\bfrom jobs\b"),
    re.compile(r"\bimport jobs\b"),
    re.compile(r"jobs\.fetchers"),
]


def _py_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


class TestNoParentImports(unittest.TestCase):
    def test_no_forbidden_imports(self):
        violations = []
        for path in _py_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.split(".")[0]]
                for name in names:
                    if name in FORBIDDEN_MODS:
                        violations.append(f"{path.relative_to(ROOT)} imports {name}")
        self.assertEqual(violations, [])

    def test_no_forbidden_strings_in_src(self):
        hits = []
        for path in _py_files():
            text = path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_TEXT:
                if pattern.search(text):
                    hits.append(f"{path.relative_to(ROOT)} matches {pattern.pattern}")
        self.assertEqual(hits, [])

    def test_paths_stay_inside_package(self):
        from electronics_research_agent.paths import CONFIG_DIR, DATA_DIR, PACKAGE_ROOT, SW_DIR

        self.assertEqual(PACKAGE_ROOT.name, "electronics_research_agent")
        for folder in (DATA_DIR, CONFIG_DIR, SW_DIR):
            self.assertTrue(str(folder).startswith(str(PACKAGE_ROOT)))
            self.assertTrue(folder.exists(), folder)


if __name__ == "__main__":
    unittest.main()

import ast
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def python_source(path: Path, symbol: str, label: str, explanation: str) -> dict:
    text = path.read_text(encoding="utf-8")
    node = ast.parse(text)
    for part in symbol.split("."):
        matches = [
            item
            for item in node.body
            if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name == part
        ]
        if len(matches) != 1:
            raise ValueError(f"Source symbol is not unique: {path.name}:{symbol}")
        node = matches[0]
    start = min([node.lineno, *(item.lineno for item in node.decorator_list)])
    end = node.end_lineno
    if end is None:
        raise ValueError("Source symbol has no end line.")
    return {
        "label": label,
        "path": path.relative_to(ROOT).as_posix(),
        "symbol": symbol,
        "language": "python",
        "line": start,
        "end_line": end,
        "text": "\n".join(text.splitlines()[start - 1 : end]) + "\n",
        "lessons": [
            {
                "id": "explain",
                "title": label,
                "line": start,
                "end_line": end,
                "explanation": explanation,
                "analogy": "Pos kontrol mencatat penerima berkas TRK001 dan bukti yang kembali.",
            }
        ],
    }


def native_definition_sources(path: Path) -> tuple[dict, list[dict]]:
    helper = ROOT / "docs" / "how-to" / "logicapps-walkthrough" / "generate.py"
    spec = importlib.util.spec_from_file_location("workbench_native_source", helper)
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load the existing native JSON source reader.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = path.read_text(encoding="utf-8")
    nodes = module.walk_nodes(json.loads(text))
    spans = module.json_spans(text)
    rows = text.splitlines()
    references = {}
    for node in nodes:
        start, end = spans[node["pointer"]]
        detail = module.lesson(node)
        explanation = detail["why"] + " " + detail["how"] + " Output: " + detail["output"]
        references[node["id"]] = {
            "key": node["id"],
            "label": node["id"],
            "symbol": node["id"],
            "path": path.relative_to(ROOT).as_posix(),
            "language": "json",
            "line": start,
            "end_line": end,
            "text": "\n".join(rows[start - 1 : end]) + "\n",
            "lessons": [
                {
                    "id": "explain",
                    "title": node["id"],
                    "line": start,
                    "end_line": end,
                    "explanation": explanation,
                    "analogy": detail["analogy"],
                }
            ],
        }
    return references, nodes


def definition_snapshot(path: Path, language: str) -> dict:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
        "language": language,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "text": raw.decode("utf-8"),
    }

import posixpath
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from tree_sitter import Node

from app.domain.indexing import GraphEdgeType
from app.domain.parsing import SourceFile, SourceLanguage, SourceSymbol
from app.parsing.registry import ParserRegistry


@dataclass(frozen=True)
class DependencyReference:
    source_path: str
    type: GraphEdgeType
    target_name: str
    line: int
    source_symbol_id: str | None = None


def _text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _import_targets(node: Node, source: bytes, language: SourceLanguage) -> list[str]:
    statement = _text(node, source).strip()
    if language == SourceLanguage.python:
        from_match = re.match(r"from\s+([.A-Za-z_][.A-Za-z0-9_]*)\s+import\s+", statement)
        if from_match:
            return [from_match.group(1)]
        if statement.startswith("import "):
            return [item.strip().split()[0] for item in statement.removeprefix("import ").split(",")]
        return []
    matches = re.findall(r"(?:from\s+|import\s*\(|require\s*\()\s*['\"]([^'\"]+)['\"]", statement)
    if matches:
        return [matches[0]]
    bare_match = re.match(r"import\s*['\"]([^'\"]+)['\"]", statement)
    return [bare_match.group(1)] if bare_match else []


def _call_name(node: Node, source: bytes) -> str | None:
    function = node.child_by_field_name("function")
    if function is None and node.type == "new_expression":
        function = node.child_by_field_name("constructor")
    if function is None:
        return None
    identifiers = re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*", _text(function, source))
    return identifiers[-1] if identifiers else None


def _containing_symbol(path: str, line: int, symbols: list[SourceSymbol], file_by_id: dict[str, SourceFile]) -> str | None:
    candidates = [
        symbol
        for symbol in symbols
        if file_by_id[symbol.file_id].path == path and symbol.start_line <= line <= symbol.end_line
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda symbol: symbol.end_line - symbol.start_line).id


def extract_dependencies(
    files: list[SourceFile],
    symbols: list[SourceSymbol],
    sources: dict[str, bytes],
    parsers: ParserRegistry,
) -> list[DependencyReference]:
    references: list[DependencyReference] = []
    file_by_id = {file.id: file for file in files}
    for file in files:
        source = sources[file.path]
        root = parsers.create(file.language).parse(source).root_node
        stack = [root]
        while stack:
            node = stack.pop()
            line = node.start_point.row + 1
            is_import = node.type in {"import_statement", "import_from_statement"}
            function_node = node.child_by_field_name("function")
            is_dynamic_import = (
                node.type == "call_expression"
                and function_node is not None
                and _text(function_node, source) in {"require", "import"}
            )
            if is_import or is_dynamic_import:
                for target in _import_targets(node, source, file.language):
                    references.append(DependencyReference(file.path, GraphEdgeType.imports, target, line))
            if node.type in {"call", "call_expression", "new_expression"} and not is_dynamic_import:
                target = _call_name(node, source)
                if target:
                    references.append(
                        DependencyReference(
                            file.path,
                            GraphEdgeType.calls,
                            target,
                            line,
                            _containing_symbol(file.path, line, symbols, file_by_id),
                        )
                    )
            stack.extend(reversed(node.children))
    return references


def resolve_local_import(source_path: str, target: str, language: SourceLanguage, known_paths: set[str]) -> str | None:
    if language == SourceLanguage.python:
        if target.startswith("."):
            dot_count = len(target) - len(target.lstrip("."))
            parent_parts = list(PurePosixPath(source_path).parent.parts)
            keep = max(0, len(parent_parts) - (dot_count - 1))
            module_parts = parent_parts[:keep] + [part for part in target.lstrip(".").split(".") if part]
        else:
            module_parts = target.split(".")
        base = "/".join(module_parts)
        candidates = [f"{base}.py", f"{base}/__init__.py"]
    else:
        if not target.startswith("."):
            return None
        base = posixpath.normpath(posixpath.join(str(PurePosixPath(source_path).parent), target))
        suffixes = (".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs")
        candidates = [base, *(f"{base}{suffix}" for suffix in suffixes), *(f"{base}/index{suffix}" for suffix in suffixes)]
    return next((candidate for candidate in candidates if candidate in known_paths), None)

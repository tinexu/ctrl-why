from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from tree_sitter import Node

from app.domain.parsing import SourceLanguage, SourceSymbol, SymbolKind


@dataclass(frozen=True)
class SymbolCandidate:
    node: Node
    name: str
    kind: SymbolKind


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _name(node: Node, source: bytes) -> str | None:
    name_node = node.child_by_field_name("name")
    return _node_text(name_node, source) if name_node else None


def _candidate(node: Node, source: bytes, language: SourceLanguage, parent_kind: SymbolKind | None) -> SymbolCandidate | None:
    name = _name(node, source)
    if language == SourceLanguage.python:
        if node.type == "class_definition" and name:
            return SymbolCandidate(node, name, SymbolKind.class_)
        if node.type == "function_definition" and name:
            kind = SymbolKind.method if parent_kind == SymbolKind.class_ else SymbolKind.function
            return SymbolCandidate(node, name, kind)
        return None

    if node.type in {"class_declaration", "class"} and name:
        return SymbolCandidate(node, name, SymbolKind.class_)
    if node.type == "interface_declaration" and name:
        return SymbolCandidate(node, name, SymbolKind.interface)
    if node.type == "type_alias_declaration" and name:
        return SymbolCandidate(node, name, SymbolKind.type_alias)
    if node.type in {"function_declaration", "generator_function_declaration"} and name:
        return SymbolCandidate(node, name, SymbolKind.function)
    if node.type == "method_definition" and name:
        return SymbolCandidate(node, name, SymbolKind.method)
    if node.type == "variable_declarator" and name:
        value = node.child_by_field_name("value")
        if value and value.type in {"arrow_function", "function_expression", "generator_function"}:
            return SymbolCandidate(node, name, SymbolKind.function)
    return None


def _signature(node: Node, source: bytes) -> str:
    body = node.child_by_field_name("body")
    if node.type == "variable_declarator":
        value = node.child_by_field_name("value")
        body = value.child_by_field_name("body") if value else None
    end_byte = body.start_byte if body else node.end_byte
    value = source[node.start_byte:end_byte].decode("utf-8", errors="replace").strip()
    return " ".join(value.split())[:500]


def extract_symbols(
    root: Node,
    source: bytes,
    language: SourceLanguage,
    workspace_id: str,
    file_id: str,
    relative_path: str,
) -> list[SourceSymbol]:
    symbols: list[SourceSymbol] = []

    def visit(node: Node, scope: tuple[str, ...], parent_kind: SymbolKind | None) -> None:
        candidate = _candidate(node, source, language, parent_kind)
        child_scope = scope
        child_parent_kind = parent_kind
        if candidate:
            qualified_name = ".".join((*scope, candidate.name))
            symbol_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{workspace_id}:{relative_path}:{candidate.kind.value}:{qualified_name}:{node.start_byte}",
                )
            )
            symbols.append(
                SourceSymbol(
                    id=symbol_id,
                    file_id=file_id,
                    name=candidate.name,
                    qualified_name=qualified_name,
                    kind=candidate.kind,
                    start_line=node.start_point.row + 1,
                    start_column=node.start_point.column + 1,
                    end_line=node.end_point.row + 1,
                    end_column=node.end_point.column + 1,
                    signature=_signature(node, source),
                )
            )
            child_scope = (*scope, candidate.name)
            child_parent_kind = candidate.kind
        for child in node.children:
            visit(child, child_scope, child_parent_kind)

    visit(root, (), None)
    return symbols


def count_syntax_errors(root: Node) -> int:
    count = int(root.type == "ERROR" or root.is_missing)
    return count + sum(count_syntax_errors(child) for child in root.children)

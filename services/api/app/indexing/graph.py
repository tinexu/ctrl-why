from uuid import NAMESPACE_URL, uuid5

from app.domain.indexing import GraphEdge, GraphEdgeType, GraphNode, GraphNodeType
from app.domain.parsing import SourceFile, SourceSymbol
from app.indexing.dependencies import DependencyReference, resolve_local_import


def build_graph(
    workspace_id: str,
    files: list[SourceFile],
    symbols: list[SourceSymbol],
    references: list[DependencyReference],
) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes = [
        GraphNode(id=file.id, type=GraphNodeType.file, label=file.path, path=file.path, entity_id=file.id, metadata={"language": file.language.value})
        for file in files
    ]
    nodes.extend(
        GraphNode(id=symbol.id, type=GraphNodeType.symbol, label=symbol.qualified_name, entity_id=symbol.id, metadata={"kind": symbol.kind.value})
        for symbol in symbols
    )
    file_by_path = {file.path: file for file in files}
    symbols_by_name: dict[str, list[SourceSymbol]] = {}
    for symbol in symbols:
        symbols_by_name.setdefault(symbol.name, []).append(symbol)

    edges: list[GraphEdge] = []
    seen_edges: set[tuple[str, str, GraphEdgeType, int | None]] = set()

    def add_edge(source_id: str, target_id: str, edge_type: GraphEdgeType, label: str, confidence: float, line: int | None = None) -> None:
        key = (source_id, target_id, edge_type, line)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append(
            GraphEdge(
                id=str(uuid5(NAMESPACE_URL, f"{workspace_id}:{source_id}:{target_id}:{edge_type.value}:{line}")),
                source_id=source_id,
                target_id=target_id,
                type=edge_type,
                line=line,
                label=label,
                confidence=confidence,
            )
        )

    for symbol in symbols:
        add_edge(symbol.file_id, symbol.id, GraphEdgeType.contains, symbol.kind.value, 1.0)

    external_nodes: dict[str, GraphNode] = {}
    known_paths = set(file_by_path)
    for reference in references:
        source_file = file_by_path[reference.source_path]
        if reference.type == GraphEdgeType.imports:
            resolved_path = resolve_local_import(reference.source_path, reference.target_name, source_file.language, known_paths)
            if resolved_path:
                target_id = file_by_path[resolved_path].id
                confidence = 1.0
            else:
                target_id = str(uuid5(NAMESPACE_URL, f"{workspace_id}:external:{reference.target_name}"))
                external_nodes.setdefault(
                    target_id,
                    GraphNode(id=target_id, type=GraphNodeType.external_module, label=reference.target_name, metadata={}),
                )
                confidence = 0.6
            add_edge(source_file.id, target_id, GraphEdgeType.imports, reference.target_name, confidence, reference.line)
        elif reference.type == GraphEdgeType.calls:
            candidates = symbols_by_name.get(reference.target_name, [])
            if len(candidates) == 1:
                add_edge(
                    reference.source_symbol_id or source_file.id,
                    candidates[0].id,
                    GraphEdgeType.calls,
                    reference.target_name,
                    0.75,
                    reference.line,
                )

    nodes.extend(external_nodes.values())
    return nodes, edges


"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Panel,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeMouseHandler,
} from "@xyflow/react";

import type { GraphEdge, GraphNode, RepositoryIndex } from "@/lib/repository-types";
import styles from "./dashboard.module.css";

type GraphView = "overview" | "files" | "calls";
type VisualNode = GraphNode & { count?: number };
type RelationshipDetail = { source: string; target: string; line: number | null; label: string };
type VisualEdge = GraphEdge & { count: number; details: RelationshipDetail[] };
type PreparedGraph = { nodes: VisualNode[]; edges: VisualEdge[]; hiddenNodeCount: number };
type GraphNodeData = { category: string; title: string; detail: string; fullLabel: string; icon: string; count?: number };

const VIEW_LIMITS: Record<GraphView, number> = { overview: 40, files: 90, calls: 120 };
const NODE_WIDTH: Record<GraphView, number> = { overview: 230, files: 215, calls: 225 };
const NODE_HEIGHT = 72;
const nodeTypes = { graphNode: GraphNodeCard };

export function DependencyGraph({ index }: { index: RepositoryIndex }) {
  const [view, setView] = useState<GraphView>("overview");
  const [query, setQuery] = useState("");
  const [showExternal, setShowExternal] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const prepared = useMemo(() => prepareGraph(index, view, query, showExternal), [index, query, showExternal, view]);
  const { positions, loading } = useElkLayout(prepared, view);
  const graph = useMemo(() => buildFlowGraph(prepared, positions, view, selectedId, selectedEdgeId), [positions, prepared, selectedEdgeId, selectedId, view]);
  const selectedNode = prepared.nodes.find((node) => node.id === selectedId) ?? null;
  const selectedEdge = prepared.edges.find((edge) => edge.id === selectedEdgeId) ?? null;
  const selectedRelationships = selectedId
    ? prepared.edges.filter((edge) => edge.source_id === selectedId || edge.target_id === selectedId).length
    : 0;

  function switchView(nextView: GraphView) {
    setView(nextView);
    setSelectedId(null);
    setSelectedEdgeId(null);
    setQuery("");
  }

  const handleNodeClick: NodeMouseHandler = (_, node) => {
    setSelectedEdgeId(null);
    setSelectedId((current) => current === node.id ? null : node.id);
  };
  const description = view === "overview"
    ? "Top-level components with repeated imports bundled into weighted relationships."
    : view === "files"
      ? "Individual files point to the local files and packages they import."
      : "Functions and methods point to internal symbols they call.";

  return (
    <section className={`${styles.panel} ${styles.graphPanel}`}>
      <header className={styles.graphHeader}>
        <div>
          <p className={styles.eyebrow}>Interactive architecture</p>
          <h2>{view === "overview" ? "System overview" : view === "files" ? "File dependencies" : "Resolved call graph"}</h2>
          <p className={styles.graphDescription}>{description}</p>
        </div>
        <div className={styles.segmented} aria-label="Graph detail level">
          <button className={view === "overview" ? styles.activeSegment : ""} onClick={() => switchView("overview")}>Overview</button>
          <button className={view === "files" ? styles.activeSegment : ""} onClick={() => switchView("files")}>Files</button>
          <button className={view === "calls" ? styles.activeSegment : ""} onClick={() => switchView("calls")}>Calls</button>
        </div>
      </header>

      <div className={styles.graphToolbar}>
        <label className={styles.graphSearch}>
          <span>Filter graph</span>
          <input onChange={(event) => { setQuery(event.target.value); setSelectedId(null); setSelectedEdgeId(null); }} placeholder={view === "calls" ? "Search functions or methods…" : "Search components, files, or packages…"} value={query} />
        </label>
        {view !== "calls" && (
          <label className={styles.graphToggle}>
            <input checked={showExternal} onChange={(event) => { setShowExternal(event.target.checked); setSelectedId(null); setSelectedEdgeId(null); }} type="checkbox" />
            External packages
          </label>
        )}
        <div className={styles.graphCounts}>
          <strong>{prepared.nodes.length}</strong> nodes<span /><strong>{prepared.edges.length}</strong> relationships
        </div>
      </div>

      <div className={styles.graphCanvas} data-compact={zoom < 0.58}>
        {loading && <div className={styles.graphLoading}>Arranging dependency layers…</div>}
        {!loading && graph.nodes.length ? (
          <ReactFlow
            edges={graph.edges}
            fitView
            fitViewOptions={{ padding: 0.2, maxZoom: 1 }}
            key={`${view}:${showExternal}:${query}:${graph.nodes.map((node) => node.id).join("|")}`}
            maxZoom={1.7}
            minZoom={0.1}
            nodes={graph.nodes}
            nodesDraggable={false}
            nodeTypes={nodeTypes}
            onMove={(_, viewport) => setZoom(viewport.zoom)}
            onNodeClick={handleNodeClick}
            onEdgeClick={(_, edge) => { setSelectedId(null); setSelectedEdgeId((current) => current === edge.id ? null : edge.id); }}
            onPaneClick={() => { setSelectedId(null); setSelectedEdgeId(null); }}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#253442" gap={30} size={1} />
            <MiniMap bgColor="#080e15" maskColor="rgba(3, 8, 14, 0.76)" nodeColor={(node) => (node.style?.borderColor as string | undefined) ?? "#5eead4"} nodeStrokeWidth={3} pannable zoomable />
            <Controls showInteractive={false} />
            <Panel className={styles.graphLegend} position="bottom-left">
              {view === "overview" && <span data-color="component">Component</span>}
              {view === "files" && <span data-color="file">Local file</span>}
              {view === "calls" && <span data-color="symbol">Function or method</span>}
              {showExternal && view !== "calls" && <span data-color="external">External package</span>}
            </Panel>
          </ReactFlow>
        ) : !loading ? (
          <div className={styles.graphEmpty}>
            <strong>{query ? "No matching relationships" : view === "calls" ? "No internal calls resolved" : "No imports detected"}</strong>
            <span>{query ? "Try a broader name." : "The analyzer did not find relationships for this view."}</span>
          </div>
        ) : null}
      </div>

      <footer className={styles.graphFooter}>
        <span>{prepared.hiddenNodeCount ? `${prepared.hiddenNodeCount} lower-connectivity nodes hidden` : "ELK layered layout · connected nodes only"}</span>
        {selectedEdge
          ? <strong>{selectedEdge.count} {view === "calls" ? "call" : "import"}{selectedEdge.count === 1 ? "" : "s"} selected</strong>
          : selectedNode
          ? <strong title={selectedNode.label}>{selectedNode.label} · {selectedRelationships} direct relationship{selectedRelationships === 1 ? "" : "s"}</strong>
          : <span>Select a node to focus, or an edge to inspect its relationships</span>}
      </footer>
      {selectedEdge && <RelationshipInspector edge={selectedEdge} view={view} onClose={() => setSelectedEdgeId(null)} />}
    </section>
  );
}

function prepareGraph(index: RepositoryIndex, view: GraphView, query: string, showExternal: boolean): PreparedGraph {
  const base = view === "overview" ? aggregateComponents(index, showExternal) : directGraph(index, view, showExternal);
  const normalizedQuery = query.trim().toLowerCase();
  const degree = new Map<string, number>();
  base.edges.forEach((edge) => {
    degree.set(edge.source_id, (degree.get(edge.source_id) ?? 0) + edge.count);
    degree.set(edge.target_id, (degree.get(edge.target_id) ?? 0) + edge.count);
  });
  let nodes = base.nodes;
  if (normalizedQuery) {
    const matching = new Set(nodes.filter((node) => `${node.label} ${node.path ?? ""}`.toLowerCase().includes(normalizedQuery)).map((node) => node.id));
    const visible = new Set(matching);
    base.edges.forEach((edge) => {
      if (matching.has(edge.source_id)) visible.add(edge.target_id);
      if (matching.has(edge.target_id)) visible.add(edge.source_id);
    });
    nodes = nodes.filter((node) => visible.has(node.id));
  }
  nodes = [...nodes].sort((left, right) => (degree.get(right.id) ?? 0) - (degree.get(left.id) ?? 0) || left.label.localeCompare(right.label));
  const hiddenNodeCount = Math.max(0, nodes.length - VIEW_LIMITS[view]);
  nodes = nodes.slice(0, VIEW_LIMITS[view]);
  const ids = new Set(nodes.map((node) => node.id));
  const edges = base.edges.filter((edge) => ids.has(edge.source_id) && ids.has(edge.target_id));
  return { nodes, edges, hiddenNodeCount };
}

function directGraph(index: RepositoryIndex, view: GraphView, showExternal: boolean): { nodes: VisualNode[]; edges: VisualEdge[] } {
  const edgeType = view === "calls" ? "calls" : "imports";
  const nodeById = new Map(index.nodes.map((node) => [node.id, node]));
  let edges = index.edges.filter((edge) => edge.type === edgeType);
  if (!showExternal) edges = edges.filter((edge) => nodeById.get(edge.target_id)?.type !== "external_module");
  const ids = new Set(edges.flatMap((edge) => [edge.source_id, edge.target_id]));
  return {
    nodes: [...ids].map((id) => nodeById.get(id)).filter((node): node is GraphNode => Boolean(node)),
    edges: edges.map((edge) => ({
      ...edge,
      count: 1,
      details: [{
        source: nodeById.get(edge.source_id)?.path ?? nodeById.get(edge.source_id)?.label ?? edge.source_id,
        target: nodeById.get(edge.target_id)?.path ?? nodeById.get(edge.target_id)?.label ?? edge.target_id,
        line: edge.line,
        label: edge.label,
      }],
    })),
  };
}

function aggregateComponents(index: RepositoryIndex, showExternal: boolean): { nodes: VisualNode[]; edges: VisualEdge[] } {
  const nodeById = new Map(index.nodes.map((node) => [node.id, node]));
  const componentByFile = new Map<string, string>();
  const components = new Map<string, VisualNode>();
  index.nodes.filter((node) => node.type === "file").forEach((node) => {
    const component = componentName(node.path ?? node.label);
    const id = `component:${component}`;
    componentByFile.set(node.id, id);
    const current = components.get(id);
    components.set(id, current
      ? { ...current, count: (current.count ?? 0) + 1 }
      : { ...node, id, label: component, path: component, metadata: { kind: "component" }, count: 1 });
  });
  const edges = new Map<string, VisualEdge>();
  const externalNodes = new Map<string, VisualNode>();
  index.edges.filter((edge) => edge.type === "imports").forEach((edge) => {
    const source = componentByFile.get(edge.source_id);
    const targetNode = nodeById.get(edge.target_id);
    if (!source || !targetNode) return;
    const target = targetNode.type === "external_module" ? targetNode.id : componentByFile.get(targetNode.id);
    if (!target || source === target || (!showExternal && targetNode.type === "external_module")) return;
    if (targetNode.type === "external_module") externalNodes.set(targetNode.id, targetNode);
    const key = `${source}->${target}`;
    const existing = edges.get(key);
    const detail = {
      source: nodeById.get(edge.source_id)?.path ?? nodeById.get(edge.source_id)?.label ?? edge.source_id,
      target: targetNode.path ?? targetNode.label,
      line: edge.line,
      label: edge.label,
    };
    edges.set(key, existing
      ? { ...existing, count: existing.count + 1, details: [...existing.details, detail] }
      : { ...edge, id: `aggregate:${key}`, source_id: source, target_id: target, label: "imports", count: 1, details: [detail] });
  });
  const connected = new Set([...edges.values()].flatMap((edge) => [edge.source_id, edge.target_id]));
  return {
    nodes: [...components.values(), ...externalNodes.values()].filter((node) => connected.has(node.id)),
    edges: [...edges.values()],
  };
}

function useElkLayout(graph: PreparedGraph, view: GraphView) {
  const [positions, setPositions] = useState<Map<string, { x: number; y: number }>>(new Map());
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const width = NODE_WIDTH[view];
    void import("elkjs/lib/elk.bundled.js").then(({ default: ELK }) => new ELK()).then((engine) => engine.layout({
      id: "root",
      layoutOptions: {
        "elk.algorithm": "layered",
        "elk.direction": "RIGHT",
        "elk.edgeRouting": "ORTHOGONAL",
        "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
        "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
        "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
        "elk.spacing.nodeNode": "42",
        "elk.layered.spacing.nodeNodeBetweenLayers": "105",
        "elk.padding": "[top=35,left=35,bottom=35,right=35]",
      },
      children: graph.nodes.map((node) => ({ id: node.id, width, height: NODE_HEIGHT })),
      edges: graph.edges.map((edge) => ({ id: edge.id, sources: [edge.source_id], targets: [edge.target_id] })),
    })).then((result) => {
      if (cancelled) return;
      setPositions(new Map((result.children ?? []).map((node) => [node.id, { x: node.x ?? 0, y: node.y ?? 0 }])));
      setLoading(false);
    }).catch(() => {
      if (!cancelled) {
        setPositions(fallbackLayout(graph.nodes, width));
        setLoading(false);
      }
    });
    return () => { cancelled = true; };
  }, [graph, view]);
  return { positions, loading };
}

function buildFlowGraph(graph: PreparedGraph, positions: Map<string, { x: number; y: number }>, view: GraphView, selectedId: string | null, selectedEdgeId: string | null): { nodes: Node[]; edges: Edge[] } {
  const connected = new Set<string>();
  if (selectedId) {
    connected.add(selectedId);
    graph.edges.forEach((edge) => {
      if (edge.source_id === selectedId) connected.add(edge.target_id);
      if (edge.target_id === selectedId) connected.add(edge.source_id);
    });
  }
  const nodes: Node[] = graph.nodes.map((node) => {
    const isComponent = view === "overview" && node.type === "file";
    const color = node.type === "external_module" ? "#fbbf24" : node.type === "symbol" ? "#93c5fd" : isComponent ? "#a78bfa" : "#5eead4";
    const selected = selectedId === node.id;
    const dimmed = selectedId !== null && !connected.has(node.id);
    const title = isComponent ? node.label : node.type === "file" ? basename(node.path ?? node.label) : shortLabel(node.label);
    const detail = isComponent ? `${node.count ?? 0} source file${node.count === 1 ? "" : "s"}` : node.type === "file" ? dirname(node.path ?? node.label) : node.type === "symbol" ? node.metadata.kind : "external package";
    return {
      id: node.id,
      type: "graphNode",
      position: positions.get(node.id) ?? { x: 0, y: 0 },
      data: { category: isComponent ? "component" : node.type.replace("_", " "), title, detail: detail || "repository root", fullLabel: node.path ?? node.label, icon: isComponent ? "▦" : node.type === "file" ? "⌑" : node.type === "symbol" ? "ƒ" : "⬡", count: node.count },
      style: { width: NODE_WIDTH[view], height: NODE_HEIGHT, borderRadius: 11, borderWidth: 1, borderStyle: "solid", borderColor: selected ? color : `${color}50`, background: selected ? `${color}16` : "#101721", boxShadow: selected ? `0 0 0 2px ${color}24, 0 12px 30px #0009` : "0 7px 20px #0005", color: "#e9f0f6", opacity: dimmed ? 0.16 : 1, padding: 0, transition: "opacity 160ms ease, box-shadow 160ms ease" },
    };
  });
  const edges: Edge[] = graph.edges.map((edge) => {
    const active = !selectedId || edge.source_id === selectedId || edge.target_id === selectedId;
    const edgeSelected = selectedEdgeId === edge.id;
    const edgeDimmed = selectedEdgeId !== null && !edgeSelected;
    const color = view === "calls" ? "#7aa7d6" : view === "overview" ? "#8b7bc4" : "#668092";
    const showLabel = edge.count > 1 && (!selectedId || active);
    return {
      id: edge.id,
      source: edge.source_id,
      target: edge.target_id,
      type: "smoothstep",
      label: showLabel ? `${edge.count} ${view === "calls" ? "calls" : "imports"}` : undefined,
      labelBgBorderRadius: 5,
      labelBgPadding: [5, 3],
      labelBgStyle: { fill: "#0a1118", fillOpacity: 0.94 },
      labelStyle: { fill: "#9aa9b8", fontSize: 9, fontWeight: 600 },
      markerEnd: { type: MarkerType.ArrowClosed, color, height: 14, width: 14 },
      style: { stroke: edgeSelected ? "#5eead4" : color, strokeWidth: edgeSelected ? 3 : active && selectedId ? 2.2 : Math.min(2.5, 1 + edge.count * 0.12), opacity: edgeDimmed ? 0.08 : active ? 0.8 : 0.06 },
      zIndex: edgeSelected || active && selectedId ? 10 : 0,
    };
  });
  return { nodes, edges };
}

function fallbackLayout(nodes: VisualNode[], width: number) {
  return new Map(nodes.map((node, index) => [node.id, { x: (index % 4) * (width + 80), y: Math.floor(index / 4) * 115 }]));
}

function componentName(path: string): string {
  const parts = path.split("/");
  return parts.length > 1 ? parts[0] : "repository root";
}

function basename(path: string): string { return path.split("/").at(-1) ?? path; }
function dirname(path: string): string { const parts = path.split("/"); return parts.slice(0, -1).join("/"); }
function shortLabel(label: string): string { return label.length > 34 ? `…${label.slice(-33)}` : label; }

function RelationshipInspector({ edge, view, onClose }: { edge: VisualEdge; view: GraphView; onClose: () => void }) {
  return (
    <aside className={styles.relationshipInspector}>
      <header>
        <div>
          <p className={styles.eyebrow}>Relationship details</p>
          <h3>{edge.count} underlying {view === "calls" ? "call" : "import"}{edge.count === 1 ? "" : "s"}</h3>
        </div>
        <button aria-label="Close relationship details" onClick={onClose}>×</button>
      </header>
      <div className={styles.relationshipList}>
        {edge.details.map((detail, index) => (
          <div className={styles.relationshipRow} key={`${detail.source}:${detail.line}:${detail.target}:${index}`}>
            <code title={detail.source}>{detail.source}{detail.line ? `:${detail.line}` : ""}</code>
            <span aria-hidden="true">→</span>
            <code title={detail.target}>{detail.target}</code>
            {detail.label && detail.label !== "imports" && <small>{detail.label}</small>}
          </div>
        ))}
      </div>
    </aside>
  );
}

function GraphNodeCard({ data }: { data: GraphNodeData }) {
  return (
    <div className={styles.graphNodeContent} title={data.fullLabel}>
      <Handle className={styles.graphHandle} position={Position.Left} type="target" />
      <span className={styles.graphNodeIcon} aria-hidden="true">{data.icon}</span>
      <div><span className={styles.nodeType}>{data.category}</span><strong>{data.title}</strong><small className={styles.graphNodeDetail}>{data.detail}</small></div>
      <Handle className={styles.graphHandle} position={Position.Right} type="source" />
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";
import { Background, Controls, MarkerType, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";

import type { RepositoryIndex } from "@/lib/repository-types";
import styles from "./dashboard.module.css";

type GraphView = "architecture" | "symbols";

export function DependencyGraph({ index }: { index: RepositoryIndex }) {
  const [view, setView] = useState<GraphView>("architecture");
  const graph = useMemo(() => buildFlowGraph(index, view), [index, view]);

  return (
    <section className={`${styles.panel} ${styles.graphPanel}`}>
      <header className={styles.panelHeader}>
        <div>
          <p className={styles.eyebrow}>Interactive graph</p>
          <h2>{view === "architecture" ? "Architecture" : "Symbol dependencies"}</h2>
        </div>
        <div className={styles.segmented} aria-label="Graph detail level">
          <button className={view === "architecture" ? styles.activeSegment : ""} onClick={() => setView("architecture")}>Architecture</button>
          <button className={view === "symbols" ? styles.activeSegment : ""} onClick={() => setView("symbols")}>Symbols</button>
        </div>
      </header>
      <div className={styles.graphCanvas}>
        <ReactFlow nodes={graph.nodes} edges={graph.edges} fitView minZoom={0.15} maxZoom={1.8} proOptions={{ hideAttribution: true }}>
          <Background color="#263342" gap={24} size={1} />
          <MiniMap
            bgColor="#0b1119"
            maskColor="rgba(3, 8, 14, 0.72)"
            nodeColor={(node) => node.style?.borderColor as string ?? "#5eead4"}
            nodeStrokeWidth={3}
            pannable
            zoomable
          />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </section>
  );
}

function buildFlowGraph(index: RepositoryIndex, view: GraphView): { nodes: Node[]; edges: Edge[] } {
  const included = index.nodes.filter((node) => view === "symbols" || node.type !== "symbol");
  const includedIds = new Set(included.map((node) => node.id));
  const groups = {
    file: included.filter((node) => node.type === "file"),
    symbol: included.filter((node) => node.type === "symbol"),
    external_module: included.filter((node) => node.type === "external_module"),
  };
  const positions = new Map<string, { x: number; y: number }>();
  groups.file.forEach((node, index) => positions.set(node.id, { x: 40 + (index % 3) * 240, y: 50 + Math.floor(index / 3) * 130 }));
  groups.symbol.forEach((node, index) => positions.set(node.id, { x: 800 + (index % 3) * 220, y: 40 + Math.floor(index / 3) * 115 }));
  groups.external_module.forEach((node, index) => positions.set(node.id, { x: view === "symbols" ? 1500 : 800, y: 50 + index * 105 }));

  const nodes: Node[] = included.map((node) => {
    const color = node.type === "file" ? "#5eead4" : node.type === "symbol" ? "#93c5fd" : "#fbbf24";
    return {
      id: node.id,
      position: positions.get(node.id) ?? { x: 0, y: 0 },
      data: { label: <div><span className={styles.nodeType}>{node.type.replace("_", " ")}</span><strong>{shortLabel(node.label)}</strong>{node.path && <small>{node.path}</small>}</div> },
      style: { width: 190, borderRadius: 10, border: `1px solid ${color}55`, borderColor: color, background: "#101721", color: "#e9f0f6", padding: 11, fontSize: 11 },
    };
  });
  const edges: Edge[] = index.edges
    .filter((edge) => includedIds.has(edge.source_id) && includedIds.has(edge.target_id))
    .map((edge) => ({
      id: edge.id,
      source: edge.source_id,
      target: edge.target_id,
      label: edge.type,
      markerEnd: { type: MarkerType.ArrowClosed, color: edge.type === "calls" ? "#93c5fd" : "#64748b" },
      style: { stroke: edge.type === "calls" ? "#57799e" : "#506070", strokeWidth: 1.2 },
      labelStyle: { fill: "#8b9bae", fontSize: 9 },
      labelBgStyle: { fill: "#0b1119", fillOpacity: 0.9 },
    }));
  return { nodes, edges };
}

function shortLabel(label: string): string {
  return label.length > 30 ? `…${label.slice(-29)}` : label;
}

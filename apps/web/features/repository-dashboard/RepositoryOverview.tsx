import type { RepositoryIndex } from "@/lib/repository-types";

import styles from "./dashboard.module.css";

const ENTRYPOINT_NAMES = new Set(["main.py", "app.py", "server.py", "index.js", "index.ts", "index.tsx", "main.js", "main.ts"]);

export function RepositoryOverview({ index }: { index: RepositoryIndex }) {
  const languages = Object.entries(index.stats.languages).sort((left, right) => right[1] - left[1]);
  const primaryLanguage = languages[0]?.[0] ?? "unknown";
  const externalModules = index.nodes.filter((node) => node.type === "external_module");
  const entryPoints = index.files.filter((file) => ENTRYPOINT_NAMES.has(file.path.split("/").at(-1) ?? ""));
  const summary = `This is primarily a ${displayLanguage(primaryLanguage)} repository with ${index.stats.file_count} supported source files and ${index.stats.symbol_count} discovered symbols. The index found ${index.stats.edge_count} structural relationships and ${externalModules.length} external module${externalModules.length === 1 ? "" : "s"}.`;

  return (
    <section className={`${styles.panel} ${styles.overview}`}>
      <div>
        <p className={styles.eyebrow}>Structural overview</p>
        <h2>What’s in this repository?</h2>
        <p className={styles.summary}>{summary}</p>
      </div>
      <div className={styles.metrics}>
        <Metric value={index.stats.file_count} label="Source files" />
        <Metric value={index.stats.symbol_count} label="Symbols" />
        <Metric value={index.stats.edge_count} label="Relationships" />
        <Metric value={index.stats.chunk_count} label="Code chunks" />
      </div>
      <div className={styles.overviewDetails}>
        <div><h3>Languages</h3><ul>{languages.map(([language, count]) => <li key={language}><span>{displayLanguage(language)}</span><strong>{count}</strong></li>)}</ul></div>
        <div><h3>Likely entry points</h3>{entryPoints.length ? <ul>{entryPoints.slice(0, 6).map((file) => <li key={file.id}><span>{file.path}</span></li>)}</ul> : <p className={styles.muted}>No conventional entry-point filename was detected.</p>}</div>
        <div><h3>External modules</h3>{externalModules.length ? <ul>{externalModules.slice(0, 8).map((node) => <li key={node.id}><span>{node.label}</span></li>)}</ul> : <p className={styles.muted}>No external imports were detected.</p>}</div>
      </div>
    </section>
  );
}

function Metric({ value, label }: { value: number; label: string }) {
  return <div className={styles.metric}><strong>{value.toLocaleString()}</strong><span>{label}</span></div>;
}

function displayLanguage(value: string): string {
  return value === "tsx" ? "TSX" : value.charAt(0).toUpperCase() + value.slice(1);
}


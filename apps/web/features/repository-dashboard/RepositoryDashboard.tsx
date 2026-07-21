"use client";

import { useState } from "react";

import type { RepositoryIndex, RepositoryWorkspace } from "@/lib/repository-types";

import { DependencyGraph } from "./DependencyGraph";
import { FileTree } from "./FileTree";
import { RepositoryOverview } from "./RepositoryOverview";
import { RepositoryChat } from "./RepositoryChat";
import { PullRequestAnalysis } from "./PullRequestAnalysis";
import { CICopilot } from "./CICopilot";
import styles from "./dashboard.module.css";

type DashboardView = "explore" | "ask" | "review" | "ci";

const VIEWS: Array<{ id: DashboardView; label: string; description: string }> = [
  { id: "explore", label: "Explore", description: "Architecture and dependencies" },
  { id: "ask", label: "Ask", description: "Grounded repository chat" },
  { id: "review", label: "Review change", description: "Diff impact and risk" },
  { id: "ci", label: "Debug CI", description: "Pipeline failure analysis" },
];

export function RepositoryDashboard({
  repository,
  index,
  onReset,
}: {
  repository: RepositoryWorkspace;
  index: RepositoryIndex;
  onReset: () => Promise<void>;
}) {
  const [view, setView] = useState<DashboardView>("explore");

  return (
    <main className={styles.dashboard}>
      <header className={styles.topbar}>
        <div className={styles.brand}><span className={styles.brandMark}>?</span><span>WTF Does This Repo Do?</span></div>
        <div className={styles.repositoryIdentity}>
          <span className={styles.readyDot} />
          <div><strong>{repository.name}</strong><small>Indexed {new Date(index.indexed_at).toLocaleTimeString()}</small></div>
        </div>
        <button className={styles.resetButton} onClick={() => void onReset()}>Analyze another repo</button>
      </header>

      <div className={styles.workspace}>
        <aside className={`${styles.panel} ${styles.sidebar}`}>
          <div className={styles.sidebarHeader}>
            <div><p className={styles.eyebrow}>Repository</p><h2>Files</h2></div>
            <span>{index.files.length}</span>
          </div>
          <div className={styles.treeScroll}><FileTree files={index.files} /></div>
          <footer className={styles.sidebarFooter}>
            <span>Temporary workspace</span>
            <strong>Expires {new Date(repository.expires_at).toLocaleTimeString()}</strong>
          </footer>
        </aside>

        <div className={styles.mainColumn}>
          <nav aria-label="Repository tools" className={styles.toolNavigation}>
            {VIEWS.map((item) => (
              <button
                aria-current={view === item.id ? "page" : undefined}
                className={view === item.id ? styles.activeTool : undefined}
                key={item.id}
                onClick={() => setView(item.id)}
                type="button"
              >
                <strong>{item.label}</strong>
                <span>{item.description}</span>
              </button>
            ))}
          </nav>

          <div className={styles.viewPane} hidden={view !== "explore"}>
            <RepositoryOverview index={index} />
            <DependencyGraph index={index} />
          </div>
          <div className={styles.viewPane} hidden={view !== "ask"}>
            <RepositoryChat workspaceId={repository.id} />
          </div>
          <div className={styles.viewPane} hidden={view !== "review"}>
            <PullRequestAnalysis workspaceId={repository.id} />
          </div>
          <div className={styles.viewPane} hidden={view !== "ci"}>
            <CICopilot workspaceId={repository.id} />
          </div>
        </div>
      </div>
    </main>
  );
}

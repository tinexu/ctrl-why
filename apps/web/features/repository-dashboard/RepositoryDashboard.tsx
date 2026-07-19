"use client";

import type { RepositoryIndex, RepositoryWorkspace } from "@/lib/repository-types";

import { DependencyGraph } from "./DependencyGraph";
import { FileTree } from "./FileTree";
import { RepositoryOverview } from "./RepositoryOverview";
import styles from "./dashboard.module.css";

export function RepositoryDashboard({
  repository,
  index,
  onReset,
}: {
  repository: RepositoryWorkspace;
  index: RepositoryIndex;
  onReset: () => Promise<void>;
}) {
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
          <RepositoryOverview index={index} />
          <DependencyGraph index={index} />
        </div>
      </div>
    </main>
  );
}


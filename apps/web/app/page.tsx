"use client";

import { FormEvent, useState } from "react";

import { deleteRepository, importGitHubRepository, indexRepository } from "@/lib/api";
import type { RepositoryIndex, RepositoryWorkspace } from "@/lib/repository-types";
import { RepositoryDashboard } from "@/features/repository-dashboard/RepositoryDashboard";
import styles from "./page.module.css";

export default function Home() {
  const [url, setUrl] = useState("");
  const [repository, setRepository] = useState<RepositoryWorkspace | null>(null);
  const [index, setIndex] = useState<RepositoryIndex | null>(null);
  const [error, setError] = useState("");
  const [stage, setStage] = useState<"idle" | "importing" | "indexing">("idle");

  async function ingestRepository(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setRepository(null);
    setIndex(null);
    setStage("importing");

    try {
      const importedRepository = await importGitHubRepository(url);
      setRepository(importedRepository);
      setStage("indexing");
      setIndex(await indexRepository(importedRepository.id));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The API could not be reached. Is it running?",
      );
    } finally {
      setStage("idle");
    }
  }

  async function reset() {
    if (repository) await deleteRepository(repository.id).catch(() => undefined);
    setRepository(null);
    setIndex(null);
    setError("");
    setUrl("");
  }

  async function retryIndexing() {
    if (!repository) return;
    setError("");
    setStage("indexing");
    try {
      setIndex(await indexRepository(repository.id));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Repository analysis failed.");
    } finally {
      setStage("idle");
    }
  }

  if (repository && index) {
    return <RepositoryDashboard repository={repository} index={index} onReset={reset} />;
  }

  return (
    <main className={styles.main}>
      <section className={styles.content}>
        <p className={styles.eyebrow}>Codebase intelligence</p>
        <h1 className={styles.title}>WTF does this repo do?</h1>
        <p className={styles.description}>
          Start with a public GitHub repository. We’ll import it into a temporary, isolated workspace for analysis.
        </p>

        <form aria-busy={stage !== "idle"} className={styles.form} onSubmit={ingestRepository}>
          <label className={styles.label} htmlFor="repository-url">
            GitHub repository URL
          </label>
          <div className={styles.inputRow}>
            <input
              className={styles.input}
              disabled={stage !== "idle"}
              id="repository-url"
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://github.com/owner/repository"
              required
              type="url"
              value={url}
            />
            <button className={styles.button} disabled={stage !== "idle"} type="submit">
              {stage === "importing" ? "Importing…" : stage === "indexing" ? "Analyzing…" : "Analyze repo"}
            </button>
          </div>
        </form>

        {error && <p className={styles.error} role="alert"><strong>Analysis stopped.</strong>{error}</p>}

        {stage !== "idle" && <AnalysisProgress repository={repository} stage={stage} />}

        {repository && !index && stage === "idle" && (
          <article className={styles.card}>
            <p className={styles.cardLabel}>Import complete · analysis incomplete</p>
            <h2 className={styles.cardTitle}>{repository.name}</h2>
            <p className={styles.cardDescription}>
              The repository is still available in its temporary workspace. Retry indexing without downloading it again.
            </p>
            <dl className={styles.metadata}>
              <div><dt>Source</dt><dd>GitHub</dd></div>
              <div><dt>Files</dt><dd>{repository.file_count}</dd></div>
              <div><dt>Size</dt><dd>{formatBytes(repository.total_bytes)}</dd></div>
              <div><dt>Expires</dt><dd>{new Date(repository.expires_at).toLocaleTimeString()}</dd></div>
            </dl>
            <div className={styles.recoveryActions}>
              <button className={styles.button} onClick={() => void retryIndexing()} type="button">Retry analysis</button>
              <button className={styles.secondaryButton} onClick={() => void reset()} type="button">Start over</button>
            </div>
          </article>
        )}
      </section>
    </main>
  );
}

function AnalysisProgress({
  repository,
  stage,
}: {
  repository: RepositoryWorkspace | null;
  stage: "importing" | "indexing";
}) {
  return (
    <article aria-live="polite" className={styles.progressCard}>
      <div className={styles.progressHeading}>
        <div>
          <p className={styles.cardLabel}>Analysis in progress</p>
          <h2>{stage === "importing" ? "Creating a safe workspace" : `Understanding ${repository?.name ?? "the repository"}`}</h2>
        </div>
        <span className={styles.spinner} aria-hidden="true" />
      </div>
      <ol className={styles.progressSteps}>
        <ProgressStep active={stage === "importing"} complete={stage === "indexing"} label="Import repository" detail="Download, validate, and remove Git metadata" />
        <ProgressStep active={stage === "indexing"} complete={false} label="Parse and index" detail="Extract symbols, dependencies, calls, and searchable chunks" />
        <ProgressStep active={false} complete={false} label="Open workspace" detail="Prepare the explorer, graph, chat, and review tools" />
      </ol>
      <p className={styles.progressNote}>Large repositories can take up to two minutes. Repository code is never executed.</p>
    </article>
  );
}

function ProgressStep({ active, complete, label, detail }: { active: boolean; complete: boolean; label: string; detail: string }) {
  return (
    <li data-state={complete ? "complete" : active ? "active" : "pending"}>
      <span>{complete ? "✓" : active ? "•" : ""}</span>
      <div><strong>{label}</strong><small>{detail}</small></div>
    </li>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

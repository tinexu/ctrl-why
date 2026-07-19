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

        <form className={styles.form} onSubmit={ingestRepository}>
          <label className={styles.label} htmlFor="repository-url">
            GitHub repository URL
          </label>
          <div className={styles.inputRow}>
            <input
              className={styles.input}
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

        {error && <p className={styles.error}>{error}</p>}

        {repository && !index && (
          <article className={styles.card}>
            <p className={styles.cardLabel}>Repository imported</p>
            <h2 className={styles.cardTitle}>{repository.name}</h2>
            <p className={styles.cardDescription}>
              {stage === "indexing" ? "Parsing files and building the dependency index…" : "Analysis could not be completed."}
            </p>
            <dl className={styles.metadata}>
              <div><dt>Source</dt><dd>GitHub</dd></div>
              <div><dt>Files</dt><dd>{repository.file_count}</dd></div>
              <div><dt>Size</dt><dd>{formatBytes(repository.total_bytes)}</dd></div>
              <div><dt>Expires</dt><dd>{new Date(repository.expires_at).toLocaleTimeString()}</dd></div>
            </dl>
          </article>
        )}
      </section>
    </main>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

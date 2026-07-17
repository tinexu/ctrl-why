"use client";

import { FormEvent, useState } from "react";

import styles from "./page.module.css";

type RepositoryWorkspace = {
  id: string;
  name: string;
  source_type: "github" | "upload";
  source_reference: string;
  created_at: string;
  expires_at: string;
  file_count: number;
  total_bytes: number;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [url, setUrl] = useState("");
  const [repository, setRepository] = useState<RepositoryWorkspace | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function ingestRepository(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setRepository(null);
    setLoading(true);

    try {
      const response = await fetch(`${apiUrl}/api/v1/repositories/github`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_url: url }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "The repository could not be imported.");
      }
      setRepository(body);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The API could not be reached. Is it running?",
      );
    } finally {
      setLoading(false);
    }
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
            <button className={styles.button} disabled={loading} type="submit">
              {loading ? "Importing…" : "Import repo"}
            </button>
          </div>
        </form>

        {error && <p className={styles.error}>{error}</p>}

        {repository && (
          <article className={styles.card}>
            <p className={styles.cardLabel}>Repository imported</p>
            <h2 className={styles.cardTitle}>{repository.name}</h2>
            <p className={styles.cardDescription}>
              Ready for analysis in temporary workspace {repository.id}.
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

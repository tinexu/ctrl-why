"use client";

import { FormEvent, useState } from "react";

import { analyzeCIFailure } from "@/lib/api";
import type { CIAnalysisResponse } from "@/lib/repository-types";

import styles from "./dashboard.module.css";

export function CICopilot({ workspaceId }: { workspaceId: string }) {
  const [workflow, setWorkflow] = useState("");
  const [logs, setLogs] = useState("");
  const [analysis, setAnalysis] = useState<CIAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      setAnalysis(await analyzeCIFailure(workspaceId, logs, workflow));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The pipeline logs could not be analyzed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className={`${styles.panel} ${styles.ciPanel}`}>
      <div className={styles.ciHeader}>
        <div>
          <p className={styles.eyebrow}>Pipeline investigation</p>
          <h2>CI/CD Copilot</h2>
          <p>Paste the failed step output. We’ll connect its errors to indexed repository code.</p>
        </div>
        {analysis && (
          <div className={styles.failureBadge} data-category={analysis.category}>
            <span>{analysis.category}</span>
            <strong>{Math.round(analysis.confidence * 100)}% confidence</strong>
          </div>
        )}
      </div>

      <form className={styles.ciForm} onSubmit={submit}>
        <input
          aria-label="Workflow name"
          onChange={(event) => setWorkflow(event.target.value)}
          placeholder="Workflow or job name (optional)"
          value={workflow}
        />
        <textarea
          aria-label="CI failure logs"
          onChange={(event) => setLogs(event.target.value)}
          placeholder={"Run pytest\nFAILED tests/test_users.py::test_create_user\nAssertionError: expected 201, received 422\nProcess completed with exit code 1"}
          required
          spellCheck={false}
          value={logs}
        />
        <div className={styles.ciActions}>
          <span>Credentials are redacted from extracted evidence before AI enhancement.</span>
          <button disabled={loading || logs.trim().length < 10} type="submit">
            {loading ? "Investigating…" : "Explain failure"}
          </button>
        </div>
      </form>
      {error && <p className={styles.searchError}>{error}</p>}

      {analysis && (
        <div className={styles.ciResults}>
          <section className={styles.ciDiagnosis}>
            <span>{analysis.ai_enhanced ? "AI-enhanced diagnosis" : "Deterministic diagnosis"}</span>
            <h3>{analysis.summary}</h3>
            <p><b>Likely root cause</b>{analysis.likely_root_cause}</p>
          </section>

          <div className={styles.ciColumns}>
            <CIList title="Affected files" items={analysis.affected_files} code empty="No indexed file was matched." />
            <CIList title="Recommended fixes" items={analysis.recommendations} />
            <CIList title="Validate the fix" items={analysis.validation_steps} />
          </div>

          <div className={styles.ciEvidenceGrid}>
            <section>
              <h3>Failure evidence <span>{analysis.log_evidence.length}</span></h3>
              <div className={styles.logEvidence}>
                {analysis.log_evidence.map((item) => (
                  <p key={item.reference}><b>[L{item.reference}]</b><small>line {item.line}</small><code>{item.content}</code></p>
                ))}
              </div>
            </section>
            <section>
              <h3>Repository evidence <span>{analysis.repository_evidence.length}</span></h3>
              <div className={styles.repoEvidence}>
                {analysis.repository_evidence.map((item, index) => (
                  <details key={item.chunk_id}>
                    <summary><b>[R{index + 1}]</b><code>{item.path}:{item.start_line}-{item.end_line}</code></summary>
                    <p>{item.reason}</p>
                    <pre>{item.excerpt}</pre>
                  </details>
                ))}
                {!analysis.repository_evidence.length && <p className={styles.emptyFinding}>No relevant source chunk was found.</p>}
              </div>
            </section>
          </div>
        </div>
      )}
    </section>
  );
}

function CIList({
  title,
  items,
  code = false,
  empty = "No recommendations available.",
}: {
  title: string;
  items: string[];
  code?: boolean;
  empty?: string;
}) {
  return (
    <section className={styles.ciList}>
      <h3>{title}<span>{items.length}</span></h3>
      {items.length ? (
        <ul>{items.map((item) => <li key={item}>{code ? <code>{item}</code> : item}</li>)}</ul>
      ) : <p>{empty}</p>}
    </section>
  );
}

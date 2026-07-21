"use client";

import { FormEvent, ReactNode, useState } from "react";

import { analyzePullRequest } from "@/lib/api";
import type { PullRequestAnalysisResponse, PullRequestFinding } from "@/lib/repository-types";

import styles from "./dashboard.module.css";

export function PullRequestAnalysis({ workspaceId }: { workspaceId: string }) {
  const [title, setTitle] = useState("");
  const [diff, setDiff] = useState("");
  const [analysis, setAnalysis] = useState<PullRequestAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      setAnalysis(await analyzePullRequest(workspaceId, diff, title));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The diff could not be analyzed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className={`${styles.panel} ${styles.prPanel}`}>
      <div className={styles.prHeader}>
        <div>
          <p className={styles.eyebrow}>Change intelligence</p>
          <h2>Pull request impact</h2>
          <p>Paste a unified Git diff to trace changed symbols into their indexed dependents.</p>
        </div>
        {analysis && (
          <div className={styles.riskGauge} data-level={analysis.risk_level}>
            <strong>{analysis.risk_score}</strong>
            <span>{analysis.risk_level} risk</span>
          </div>
        )}
      </div>

      <form className={styles.prForm} onSubmit={submit}>
        <input
          aria-label="Pull request title"
          onChange={(event) => setTitle(event.target.value)}
          placeholder="PR title (optional)"
          value={title}
        />
        <textarea
          aria-label="Git diff"
          onChange={(event) => setDiff(event.target.value)}
          placeholder={"diff --git a/src/auth.ts b/src/auth.ts\n--- a/src/auth.ts\n+++ b/src/auth.ts\n@@ -10,2 +10,3 @@"}
          required
          spellCheck={false}
          value={diff}
        />
        <div className={styles.prActions}>
          <span>The repository is never executed. Diff contents are treated as untrusted input.</span>
          <button disabled={loading || diff.trim().length < 10} type="submit">
            {loading ? "Tracing impact…" : "Analyze change"}
          </button>
        </div>
      </form>
      {error && <p className={styles.searchError} role="alert">{error}</p>}

      {analysis && (
        <div className={styles.prResults}>
          <div className={styles.prSummary}>
            <span>{analysis.ai_enhanced ? "AI-enhanced · grounded in static analysis" : "Static analysis"}</span>
            <p>{analysis.summary}</p>
          </div>

          <div className={styles.impactGrid}>
            <ResultGroup title="Changed files" count={analysis.changed_files.length}>
              {analysis.changed_files.map((file) => (
                <article className={styles.fileImpact} key={file.path}>
                  <div><code>{file.path}</code><span data-kind={file.kind}>{file.kind}</span></div>
                  <small><b>+{file.additions}</b> −{file.deletions} · {file.indexed ? "matched to index" : "not in current index"}</small>
                  {file.changed_symbols.length > 0 && <p>{file.changed_symbols.join(", ")}</p>}
                </article>
              ))}
            </ResultGroup>

            <ResultGroup title="Affected dependents" count={analysis.affected_files.length} empty="No indexed dependents found.">
              {analysis.affected_files.map((file) => (
                <article className={styles.fileImpact} key={file.path}>
                  <code>{file.path}{file.evidence_line ? `:${file.evidence_line}` : ""}</code>
                  <small>{file.relationship} · {Math.round(file.confidence * 100)}% confidence</small>
                </article>
              ))}
            </ResultGroup>
          </div>

          <div className={styles.reviewGrid}>
            <Findings title="What could break" findings={analysis.breaking_risks} empty="No graph-backed breaking risk detected." />
            <Findings title="Security review" findings={analysis.security_concerns} empty="No suspicious added-line pattern detected." />
            <ResultGroup title="Suggested tests" count={analysis.suggested_tests.length}>
              <ol className={styles.testList}>
                {analysis.suggested_tests.map((test) => <li key={test}>{test}</li>)}
              </ol>
            </ResultGroup>
          </div>

          <details className={styles.evidencePanel}>
            <summary>Evidence map <span>{analysis.evidence.length} changed locations</span></summary>
            {analysis.evidence.map((item) => (
              <p key={item.reference}><b>[{item.reference}]</b> <code>{item.path}:{item.start_line}-{item.end_line}</code> {item.description}</p>
            ))}
          </details>
        </div>
      )}
    </section>
  );
}

function ResultGroup({
  title,
  count,
  empty,
  children,
}: {
  title: string;
  count: number;
  empty?: string;
  children: ReactNode;
}) {
  return (
    <section className={styles.resultGroup}>
      <h3>{title}<span>{count}</span></h3>
      {count ? children : <p className={styles.emptyFinding}>{empty}</p>}
    </section>
  );
}

function Findings({ title, findings, empty }: { title: string; findings: PullRequestFinding[]; empty: string }) {
  return (
    <ResultGroup title={title} count={findings.length} empty={empty}>
      {findings.map((finding, index) => (
        <article className={styles.finding} data-level={finding.severity} key={`${finding.title}-${index}`}>
          <div><span>{finding.severity}</span><strong>{finding.title}</strong></div>
          <p>{finding.explanation}</p>
          {finding.evidence.length > 0 && <small>Evidence {finding.evidence.map((item) => `[${item}]`).join(" ")}</small>}
        </article>
      ))}
    </ResultGroup>
  );
}

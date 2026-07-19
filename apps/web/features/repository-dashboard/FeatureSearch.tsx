"use client";

import { FormEvent, useState } from "react";

import { searchRepository } from "@/lib/api";
import type { RepositorySearchResult } from "@/lib/repository-types";

import styles from "./dashboard.module.css";

export function FeatureSearch({ workspaceId }: { workspaceId: string }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RepositorySearchResult[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  async function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await searchRepository(workspaceId, query.trim());
      setResults(response.results);
      setHasSearched(true);
    } catch (requestError) {
      setResults([]);
      setHasSearched(true);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The repository could not be searched.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className={`${styles.panel} ${styles.searchPanel}`}>
      <div className={styles.searchIntro}>
        <p className={styles.eyebrow}>Feature finder</p>
        <h2>Where does this code live?</h2>
        <p>
          Describe a feature or behavior. We’ll rank the files and symbols most likely to implement it.
        </p>
      </div>

      <form className={styles.searchForm} onSubmit={submitSearch}>
        <label className={styles.searchLabel} htmlFor="feature-query">
          Feature or behavior
        </label>
        <div className={styles.searchInputRow}>
          <input
            className={styles.searchInput}
            id="feature-query"
            maxLength={300}
            minLength={2}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Where is authentication handled?"
            required
            value={query}
          />
          <button className={styles.searchButton} disabled={loading || query.trim().length < 2} type="submit">
            {loading ? "Searching…" : "Find code"}
          </button>
        </div>
        <p className={styles.searchHint}>Try a feature, error message, function name, or domain concept.</p>
      </form>

      {error && <p className={styles.searchError}>{error}</p>}

      {hasSearched && !error && (
        <div className={styles.searchResults} aria-live="polite">
          <div className={styles.resultsHeader}>
            <h3>{results.length ? "Most relevant code" : "No matching code found"}</h3>
            {results.length > 0 && <span>{results.length} results</span>}
          </div>

          {results.length > 0 ? (
            <ol className={styles.resultList}>
              {results.map((result) => (
                <li className={styles.resultCard} key={result.chunk_id}>
                  <div className={styles.resultHeading}>
                    <div>
                      <code className={styles.resultPath}>{result.path}</code>
                      <p className={styles.resultLocation}>
                        {result.symbol ? `${displayKind(result.symbol_kind)} ${result.symbol}` : "File-level code"}
                        {` · lines ${result.start_line}–${result.end_line}`}
                      </p>
                    </div>
                    <span className={styles.resultScore}>{Math.round(result.score * 100)}% match</span>
                  </div>
                  <p className={styles.resultReason}>{result.reason}</p>
                  <pre className={styles.resultExcerpt}><code>{result.excerpt}</code></pre>
                </li>
              ))}
            </ol>
          ) : (
            <p className={styles.emptyResults}>Try a more concrete name, behavior, or term used in the code.</p>
          )}
        </div>
      )}
    </section>
  );
}

function displayKind(kind: string | null): string {
  if (!kind) return "Symbol";
  return kind.replace("_", " ").replace(/^./, (character) => character.toUpperCase());
}

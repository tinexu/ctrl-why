"use client";

import { FormEvent, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { chatWithRepository } from "@/lib/api";
import type { ChatCitation, ChatMessage, RepositorySearchResult } from "@/lib/repository-types";

import styles from "./dashboard.module.css";

type DisplayMessage = ChatMessage & {
  citations?: ChatCitation[];
  sources?: RepositorySearchResult[];
};

export function RepositoryChat({ workspaceId }: { workspaceId: string }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (trimmedQuestion.length < 2 || loading) return;

    const history = messages.map(({ role, content }) => ({ role, content }));
    setMessages((current) => [...current, { role: "user", content: trimmedQuestion }]);
    setQuestion("");
    setError("");
    setLoading(true);

    try {
      const response = await chatWithRepository(workspaceId, trimmedQuestion, history);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.answer,
          citations: response.citations,
          sources: response.sources,
        },
      ]);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The AI could not answer right now.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className={`${styles.panel} ${styles.chatPanel}`}>
      <div className={styles.searchIntro}>
        <p className={styles.eyebrow}>AI codebase advisor</p>
        <h2>Ask this repository</h2>
        <p>Ask how something works or where it lives. Get a clear answer and the exact supporting code.</p>
      </div>

      <div className={styles.chatTranscript} aria-live="polite">
        {messages.length === 0 ? (
          <div className={styles.chatEmpty}>
            <p>Try asking:</p>
            <span>“How does authentication work?”</span>
            <span>“Where does a command enter the application?”</span>
            <span>“Which files implement configuration loading?”</span>
          </div>
        ) : messages.map((message, index) => (
          <article className={styles.chatMessage} data-role={message.role} key={`${message.role}-${index}`}>
            <strong className={styles.messageAuthor}>{message.role === "user" ? "You" : "Advisor"}</strong>
            {message.role === "assistant" ? (
              <div className={styles.markdownAnswer}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              </div>
            ) : <p>{message.content}</p>}
            {message.citations && message.citations.length > 0 && (
              <div className={styles.chatCitations}>
                {message.citations.map((citation) => (
                  <code key={`${citation.reference}-${citation.path}-${citation.start_line}`}>
                    [{citation.reference}] {citation.path}:{citation.start_line}–{citation.end_line}
                  </code>
                ))}
              </div>
            )}
            {message.sources && message.sources.length > 0 && (
              <details className={styles.relevantCode}>
                <summary>Relevant code <span>{message.sources.length} matches</span></summary>
                <ol className={styles.sourceList}>
                  {message.sources.map((source) => (
                    <li className={styles.sourceCard} key={source.chunk_id}>
                      <div className={styles.sourceHeading}>
                        <div>
                          <code>{source.path}</code>
                          <small>
                            {source.symbol ?? "File-level code"} · lines {source.start_line}–{source.end_line}
                          </small>
                        </div>
                        <span>{Math.round(source.score * 100)}%</span>
                      </div>
                      <p>{source.reason}</p>
                      <pre><code>{source.excerpt}</code></pre>
                    </li>
                  ))}
                </ol>
              </details>
            )}
          </article>
        ))}
        {loading && <p className={styles.chatThinking}>Reading the relevant code…</p>}
      </div>

      {error && <p className={styles.searchError}>{error}</p>}
      <form className={styles.chatForm} onSubmit={submitQuestion}>
        <label className={styles.searchLabel} htmlFor="repository-question">Question about this repository</label>
        <div className={styles.searchInputRow}>
          <input
            className={styles.searchInput}
            id="repository-question"
            maxLength={1000}
            minLength={2}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What does this repository do?"
            required
            value={question}
          />
          <button className={styles.searchButton} disabled={loading || question.trim().length < 2} type="submit">
            {loading ? "Thinking…" : "Ask AI"}
          </button>
        </div>
      </form>
    </section>
  );
}

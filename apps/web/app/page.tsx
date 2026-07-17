import styles from "./page.module.css";

export default function Home() {
  return (
    <main className={styles.main}>
      <section className={styles.content}>
        <p className={styles.eyebrow}>Codebase intelligence</p>
        <h1 className={styles.title}>WTF does this repo do?</h1>
        <p className={styles.description}>
          Understand unfamiliar repositories, trace dependencies, and review changes with evidence from the code.
        </p>
        <div className={styles.status}>
          <span className={styles.statusDot} aria-hidden="true" />
          Application foundation is running
        </div>
      </section>
    </main>
  );
}


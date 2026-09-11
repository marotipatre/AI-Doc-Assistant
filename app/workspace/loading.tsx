import styles from "../status.module.css";

export default function Loading() {
  return (
    <main
      className={styles.page}
      aria-busy="true"
      aria-label="Loading workspace"
    >
      <section className={styles.card} role="status">
        <span className={styles.eyebrow}>REPOLENS</span>
        <h1>Opening your workspace.</h1>
        <p>Getting your repositories and saved context ready.</p>
        <div aria-hidden="true">
          <div className={styles.line} />
          <div className={styles.line} />
          <div className={styles.line} />
        </div>
      </section>
    </main>
  );
}

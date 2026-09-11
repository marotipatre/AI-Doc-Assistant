import Link from "next/link";
import { ArrowRight, BookOpen } from "lucide-react";
import styles from "./status.module.css";

export default function NotFound() {
  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <Link href="/" className={styles.eyebrow}>
          REPOLENS / 404
        </Link>
        <h1>
          This path leads
          <br />
          somewhere else.
        </h1>
        <p>
          The page may have moved, or the address may be incomplete. Your
          repositories are waiting in your workspace.
        </p>
        <div className={styles.actions}>
          <Link className={styles.primary} href="/workspace">
            Open workspace <ArrowRight size={16} />
          </Link>
          <Link href="/guide">
            <BookOpen size={16} /> Read the guide
          </Link>
        </div>
      </section>
    </main>
  );
}

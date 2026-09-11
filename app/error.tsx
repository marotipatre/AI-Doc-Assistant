"use client";

import Link from "next/link";
import { RotateCcw } from "lucide-react";
import styles from "./status.module.css";

export default function ErrorPage({
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <span className={styles.eyebrow}>REPOLENS / LET’S TRY THAT AGAIN</span>
        <h1>We couldn’t load this view.</h1>
        <p>
          Try loading it again. If the problem continues, return home and reopen
          your workspace.
        </p>
        <div className={styles.actions}>
          <button className={styles.primary} onClick={retry}>
            <RotateCcw size={16} /> Try again
          </button>
          <Link href="/">Back to home</Link>
        </div>
      </section>
    </main>
  );
}

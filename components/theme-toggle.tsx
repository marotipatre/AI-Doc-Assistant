"use client";

import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
  return (
    <button
      className="theme-toggle"
      type="button"
      aria-label="Toggle light and dark theme"
      title="Toggle light and dark theme"
      onClick={() => {
        const theme =
          document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        document.documentElement.dataset.theme = theme;
        try {
          localStorage.setItem("repolens:theme", theme);
        } catch {
          /* Theme still works when storage is unavailable. */
        }
      }}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 6,
        minWidth: 44,
        minHeight: 44,
        border: "1px solid var(--border)",
        borderRadius: 10,
        color: "var(--foreground)",
        background: "var(--surface)",
        flexShrink: 0,
      }}
    >
      <Sun size={16} aria-hidden="true" />
      <span aria-hidden="true" style={{ opacity: 0.45 }}>
        /
      </span>
      <Moon size={15} aria-hidden="true" />
    </button>
  );
}

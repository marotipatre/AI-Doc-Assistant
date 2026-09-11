import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import "./studio.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RepoLens — Create and edit repository instructions",
  description:
    "Create, edit, and download SKILL.md with setup steps, project rules, and verification checks for your repository.",
  icons: { icon: "/icon.svg" },
  openGraph: {
    title: "RepoLens — Create and edit repository instructions",
    description:
      "Choose a GitHub repository, review its files, and edit your project instructions.",
    type: "website",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('repolens:theme');document.documentElement.dataset.theme=t==='light'?'light':'dark'}catch(e){}})()`,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import { GuidePage } from "@/components/landing/landing";

export const metadata: Metadata = {
  title: "Getting started · RepoLens",
  description:
    "Connect GitHub, explore your repository, and ask questions with source evidence. A practical guide to RepoLens.",
};

export default function Guide() {
  return <GuidePage />;
}

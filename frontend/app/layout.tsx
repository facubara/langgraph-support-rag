import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "Support Copilot — multi-agent RAG assistant",
    template: "%s · Support Copilot",
  },
  description:
    "A production-style multi-agent customer-support assistant: LangGraph orchestration, RAG grounding, human-in-the-loop safety, streaming, and full-trace observability.",
  openGraph: {
    title: "Support Copilot — multi-agent RAG assistant",
    description:
      "Multi-agent orchestration, RAG grounding, human-in-the-loop safety, and full-trace observability — live demo.",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}

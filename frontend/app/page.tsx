import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  GitBranch,
  Library,
  Radio,
  ShieldCheck,
  Activity,
} from "lucide-react";
import { auth } from "@/auth";
import { Brand } from "@/components/brand";
import { GoogleButton } from "@/components/google-button";
import { DevLogin } from "@/components/dev-login";

const FEATURES = [
  {
    icon: Boxes,
    title: "Multi-agent orchestration",
    body: "A LangGraph state machine routes each turn through router, billing/RAG, policy/safety, and response agents with explicit, inspectable hand-offs.",
  },
  {
    icon: Library,
    title: "RAG grounding",
    body: "Answers are grounded in a retrieved knowledge base with score thresholds — and the assistant refuses rather than guess when nothing supports the answer.",
  },
  {
    icon: ShieldCheck,
    title: "Human-in-the-loop safety",
    body: "Risky actions like refunds and escalations pause for explicit approval. Nothing irreversible happens without a human in the loop.",
  },
  {
    icon: Radio,
    title: "Token streaming",
    body: "Responses stream token-by-token over SSE while the agent graph lights up live, so you watch the system think instead of waiting on a spinner.",
  },
  {
    icon: Activity,
    title: "Full-trace observability",
    body: "Every prompt, tool call, latency, and cost is traced. Inspect any run end to end and replay it deterministically to reproduce the outcome.",
  },
  {
    icon: GitBranch,
    title: "Evaluated & versioned",
    body: "An offline eval harness scores task success, grounding, and policy compliance, with regression diffs between prompt and model versions.",
  },
];

const NODES = ["Router", "Billing / RAG", "Policy / Safety", "Response"];

export default async function LandingPage() {
  const session = await auth();
  const signedIn = Boolean(session?.user);

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Brand />
          <nav className="flex items-center gap-3 text-sm">
            <a href="#features" className="hidden text-muted-foreground hover:text-foreground sm:inline">
              Features
            </a>
            {signedIn ? (
              <Link
                href="/app"
                className="inline-flex items-center gap-1.5 rounded-[var(--radius-md)] bg-primary px-4 py-2 font-medium text-primary-foreground transition hover:opacity-90"
              >
                Open the app <ArrowRight className="size-4" />
              </Link>
            ) : (
              <GoogleButton label="Sign in" className="px-4 py-2" />
            )}
          </nav>
        </div>
      </header>

      <main className="relative flex-1">
        <div className="pointer-events-none absolute inset-0 bg-grid opacity-60" />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-[420px] glow" />

        {/* Hero */}
        <section className="relative mx-auto max-w-6xl px-6 pt-20 pb-16 text-center">
          <span className="inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
            <span className="size-1.5 rounded-full bg-success animate-node" />
            Live demo · runs on a mock model, no setup required
          </span>
          <h1 className="mx-auto mt-6 max-w-3xl text-balance text-4xl font-semibold tracking-tighter sm:text-6xl">
            A multi-agent support assistant you can actually watch think.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-balance text-lg text-muted-foreground">
            Customer-support and billing automation built like a production agentic system —
            LangGraph orchestration, RAG grounding, human-in-the-loop safety, streaming, and
            full-trace observability with deterministic replay.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            {signedIn ? (
              <Link
                href="/app"
                className="inline-flex items-center gap-2 rounded-[var(--radius-md)] bg-primary px-6 py-3 font-medium text-primary-foreground shadow-sm transition hover:opacity-90"
              >
                Open the app <ArrowRight className="size-4" />
              </Link>
            ) : (
              <GoogleButton label="Try the live demo" className="px-6 py-3" />
            )}
            <a
              href="#features"
              className="inline-flex items-center gap-2 rounded-[var(--radius-md)] border bg-card px-6 py-3 font-medium transition hover:shadow-sm"
            >
              See what it does
            </a>
          </div>
          {!signedIn && <DevLogin className="mt-3" />}

          {/* Architecture strip */}
          <div className="mx-auto mt-16 flex max-w-3xl flex-wrap items-center justify-center gap-2 text-sm">
            {NODES.map((node, i) => (
              <span key={node} className="flex items-center gap-2">
                <span className="rounded-[var(--radius-md)] border bg-card px-4 py-2 font-medium shadow-sm">
                  {node}
                </span>
                {i < NODES.length - 1 && <ArrowRight className="size-4 text-muted-foreground" />}
              </span>
            ))}
          </div>
        </section>

        {/* Features */}
        <section id="features" className="relative mx-auto max-w-6xl px-6 pb-24">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <div
                key={title}
                className="group rounded-[var(--radius-lg)] border bg-card p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="grid size-10 place-items-center rounded-[var(--radius-md)] bg-muted text-primary">
                  <Icon className="size-5" />
                </div>
                <h3 className="mt-4 font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-8 text-sm text-muted-foreground sm:flex-row">
          <Brand />
          <p>Built as a portfolio demo · LangGraph · FastAPI · Next.js</p>
        </div>
      </footer>
    </div>
  );
}

import Link from "next/link";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

/** Wordmark used in the marketing header and the app shell. */
export function Brand({ href = "/", className }: { href?: string; className?: string }) {
  return (
    <Link href={href} className={cn("inline-flex items-center gap-2 font-semibold tracking-tight", className)}>
      <span className="grid size-7 place-items-center rounded-md bg-primary text-primary-foreground">
        <Sparkles className="size-4" />
      </span>
      <span>Support Copilot</span>
    </Link>
  );
}

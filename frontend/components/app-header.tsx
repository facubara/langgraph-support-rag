import Link from "next/link";
import { LayoutDashboard, MessagesSquare } from "lucide-react";
import { Brand } from "@/components/brand";
import { SignOutButton } from "@/components/sign-out-button";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/app", label: "Chat", icon: MessagesSquare, key: "chat" },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, key: "dashboard" },
] as const;

/** Shared top nav for the signed-in app + dashboard. */
export function AppHeader({ email, active }: { email?: string | null; active: "chat" | "dashboard" }) {
  return (
    <header className="shrink-0 border-b bg-background/80 backdrop-blur">
      <div className="flex h-14 items-center justify-between gap-4 px-4">
        <div className="flex items-center gap-6">
          <Brand href="/app" />
          <nav className="flex items-center gap-1">
            {NAV.map(({ href, label, icon: Icon, key }) => (
              <Link
                key={key}
                href={href}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-[var(--radius-md)] px-3 py-1.5 text-sm transition",
                  key === active ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="size-4" />
                {label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-muted-foreground sm:inline">{email}</span>
          <SignOutButton />
        </div>
      </div>
    </header>
  );
}

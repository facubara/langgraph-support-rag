import { signOut } from "@/auth";
import { LogOut } from "lucide-react";
import { cn } from "@/lib/utils";

/** Server-action sign-out button. */
export function SignOutButton({ className }: { className?: string }) {
  return (
    <form
      action={async () => {
        "use server";
        await signOut({ redirectTo: "/" });
      }}
    >
      <button
        type="submit"
        className={cn(
          "inline-flex items-center gap-2 rounded-[var(--radius-md)] border bg-card px-3 py-1.5 text-sm",
          "text-muted-foreground transition hover:text-foreground hover:shadow-sm cursor-pointer",
          className,
        )}
      >
        <LogOut className="size-4" />
        Sign out
      </button>
    </form>
  );
}

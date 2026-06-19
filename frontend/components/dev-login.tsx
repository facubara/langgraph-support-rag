import { FlaskConical } from "lucide-react";
import { signIn } from "@/auth";
import { cn } from "@/lib/utils";

/** Dev-only one-click sign-in. Renders nothing unless ALLOW_DEV_LOGIN=true. */
export function DevLogin({ redirectTo = "/app", className }: { redirectTo?: string; className?: string }) {
  if (process.env.ALLOW_DEV_LOGIN !== "true") return null;
  return (
    <form
      action={async () => {
        "use server";
        await signIn("dev", { redirectTo });
      }}
    >
      <button
        type="submit"
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-[var(--radius-md)] px-4 py-2 text-sm",
          "text-muted-foreground transition hover:text-foreground cursor-pointer",
          className,
        )}
      >
        <FlaskConical className="size-4" />
        Continue as demo user (dev)
      </button>
    </form>
  );
}

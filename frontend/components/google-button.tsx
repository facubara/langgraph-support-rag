import { signIn } from "@/auth";
import { cn } from "@/lib/utils";

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-[18px]" aria-hidden>
      <path
        fill="#EA4335"
        d="M12 10.2v3.9h5.5c-.24 1.4-1.66 4.1-5.5 4.1-3.3 0-6-2.7-6-6.2s2.7-6.2 6-6.2c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.9 6 14.7 5 12 5 6.9 5 2.8 9.1 2.8 14S6.9 23 12 23c6 0 9.9-4.2 9.9-10.1 0-.7-.1-1.2-.2-1.7H12z"
      />
    </svg>
  );
}

/** Server-action Google sign-in button. The whole flow runs on the server via Auth.js. */
export function GoogleButton({
  redirectTo = "/app",
  label = "Continue with Google",
  className,
}: {
  redirectTo?: string;
  label?: string;
  className?: string;
}) {
  return (
    <form
      action={async () => {
        "use server";
        await signIn("google", { redirectTo });
      }}
    >
      <button
        type="submit"
        className={cn(
          "inline-flex items-center justify-center gap-2.5 rounded-[var(--radius-md)] bg-card px-5 py-2.5",
          "text-sm font-medium text-card-foreground border shadow-sm",
          "transition hover:shadow-md hover:-translate-y-px active:translate-y-0 cursor-pointer",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          className,
        )}
      >
        <GoogleIcon />
        {label}
      </button>
    </form>
  );
}

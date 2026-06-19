import { MessagesSquare } from "lucide-react";
import { auth } from "@/auth";
import { Brand } from "@/components/brand";
import { SignOutButton } from "@/components/sign-out-button";

export default async function AppPage() {
  const session = await auth();
  const user = session!.user;

  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Brand href="/app" />
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted-foreground sm:inline">{user?.email}</span>
            <SignOutButton />
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 items-center justify-center px-6 py-16">
        <div className="rounded-[var(--radius-lg)] border bg-card p-10 text-center shadow-sm">
          <div className="mx-auto grid size-12 place-items-center rounded-[var(--radius-md)] bg-muted text-primary">
            <MessagesSquare className="size-6" />
          </div>
          <h1 className="mt-5 text-xl font-semibold">You&apos;re signed in, {user?.name?.split(" ")[0] ?? "there"}.</h1>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            The chat experience — streaming responses, a live agent graph, citations, and
            human-in-the-loop approvals — lands in the next build slice. The frontend, auth, and
            backend proxy are wired and ready.
          </p>
        </div>
      </main>
    </div>
  );
}

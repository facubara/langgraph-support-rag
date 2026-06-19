import { auth } from "@/auth";
import { Brand } from "@/components/brand";
import { SignOutButton } from "@/components/sign-out-button";
import { ChatApp } from "@/components/chat/chat-app";

export default async function AppPage() {
  const session = await auth();
  const user = session!.user;

  return (
    <div className="flex h-screen flex-col">
      <header className="shrink-0 border-b bg-background/80 backdrop-blur">
        <div className="flex h-14 items-center justify-between px-4">
          <Brand href="/app" />
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted-foreground sm:inline">{user?.email}</span>
            <SignOutButton />
          </div>
        </div>
      </header>
      <ChatApp />
    </div>
  );
}

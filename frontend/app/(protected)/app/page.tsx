import { auth } from "@/auth";
import { AppHeader } from "@/components/app-header";
import { ChatApp } from "@/components/chat/chat-app";

export default async function AppPage() {
  const session = await auth();

  return (
    <div className="flex h-screen flex-col">
      <AppHeader email={session!.user?.email} active="chat" />
      <ChatApp />
    </div>
  );
}

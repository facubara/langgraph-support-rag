import { auth } from "@/auth";
import { AppHeader } from "@/components/app-header";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader email={session!.user?.email} active="dashboard" />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>
    </div>
  );
}

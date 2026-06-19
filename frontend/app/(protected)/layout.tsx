import { redirect } from "next/navigation";
import { auth } from "@/auth";

// Server-side auth gate for everything under (protected): /app and /dashboard.
export default async function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session?.user) redirect("/");
  return <>{children}</>;
}

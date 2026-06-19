import Link from "next/link";
import { ArrowLeft, Lock } from "lucide-react";
import { getJson } from "@/lib/backend";

type SignIn = { id: number; ts: number; user_id: string; detail: { email?: string; name?: string } | null };
type AdminUser = { id: string; email: string | null; name: string | null; last_seen: number; sign_in_count: number };

function fmt(epoch: number) {
  return new Date(epoch * 1000).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default async function AdminPage() {
  let users: AdminUser[] = [];
  let signIns: SignIn[] = [];
  let forbidden = false;
  try {
    [users, signIns] = await Promise.all([
      getJson<AdminUser[]>("/admin/users"),
      getJson<SignIn[]>("/admin/sign-ins"),
    ]);
  } catch (err) {
    if ((err as { status?: number }).status === 403) forbidden = true;
    else throw err;
  }

  return (
    <div>
      <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Back to runs
      </Link>
      <h1 className="mt-4 text-2xl font-semibold tracking-tight">Sign-ins</h1>
      <p className="mt-1 text-sm text-muted-foreground">Who has entered the demo. Owner-only.</p>

      {forbidden ? (
        <div className="mt-6 flex items-center gap-3 rounded-[var(--radius-lg)] border bg-card p-6 text-sm text-muted-foreground">
          <Lock className="size-5" />
          This view is restricted to the owner (set <code className="mx-1">OWNER_EMAIL</code> on the backend).
        </div>
      ) : (
        <div className="mt-6 space-y-8">
          <section>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Users ({users.length})
            </h2>
            <div className="overflow-hidden rounded-[var(--radius-lg)] border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Name</th>
                    <th className="px-4 py-2.5 font-medium">Email</th>
                    <th className="px-4 py-2.5 font-medium">Sign-ins</th>
                    <th className="px-4 py-2.5 font-medium">Last seen</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr><td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">No users yet.</td></tr>
                  ) : (
                    users.map((u) => (
                      <tr key={u.id} className="border-t">
                        <td className="px-4 py-2.5">{u.name ?? "—"}</td>
                        <td className="px-4 py-2.5 text-muted-foreground">{u.email ?? u.id}</td>
                        <td className="px-4 py-2.5">{u.sign_in_count}</td>
                        <td className="whitespace-nowrap px-4 py-2.5 text-muted-foreground">{fmt(u.last_seen)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Recent sign-ins ({signIns.length})
            </h2>
            <ul className="space-y-1.5">
              {signIns.map((e) => (
                <li key={e.id} className="flex items-center justify-between rounded-[var(--radius-md)] border bg-card px-4 py-2.5 text-sm">
                  <span>{e.detail?.name ?? e.detail?.email ?? e.user_id}</span>
                  <span className="text-xs text-muted-foreground">{fmt(e.ts)}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}

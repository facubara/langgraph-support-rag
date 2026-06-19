import NextAuth from "next-auth";
import type { Provider } from "next-auth/providers";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";

/**
 * Auth.js (NextAuth v5) — Google sign-in.
 *
 * Reads AUTH_SECRET, AUTH_GOOGLE_ID, AUTH_GOOGLE_SECRET from the environment.
 * On sign-in we best-effort notify the FastAPI backend so the owner can see who
 * entered the demo (the endpoint is shared-secret gated; failures are swallowed
 * so a backend hiccup never blocks login).
 *
 * DEV ONLY: when ALLOW_DEV_LOGIN=true a one-click credentials provider is added so the
 * demo can be tried locally (and by reviewers) without setting up Google OAuth. Leave it
 * unset in production so only real Google identities can enter.
 */
const providers: Provider[] = [Google];
if (process.env.ALLOW_DEV_LOGIN === "true") {
  providers.push(
    Credentials({
      id: "dev",
      name: "Demo user",
      credentials: {},
      authorize: () => ({ id: "demo@local", email: "demo@local", name: "Demo User" }),
    }),
  );
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  // Trust the deployment host (required for self-hosted / proxied runs like `next start`
  // and Render; Vercel auto-detects). Avoids Auth.js UntrustedHost in production.
  trustHost: true,
  providers,
  callbacks: {
    // Expose the stable provider user id to the session so the BFF can forward it.
    session({ session, token }) {
      if (token.sub && session.user) session.user.id = token.sub;
      return session;
    },
  },
  events: {
    async signIn({ user }) {
      const backend = process.env.BACKEND_URL;
      const secret = process.env.SERVICE_SHARED_SECRET;
      if (!backend || !secret || !user.email) return;
      try {
        await fetch(`${backend}/auth/sign-in`, {
          method: "POST",
          headers: {
            "content-type": "application/json",
            "x-internal-secret": secret,
            "x-user-id": user.id ?? user.email,
            "x-user-email": user.email,
          },
          body: JSON.stringify({ user_id: user.id ?? user.email, email: user.email, name: user.name }),
        });
      } catch {
        // Non-fatal: sign-in tracking is best-effort.
      }
    },
  },
});

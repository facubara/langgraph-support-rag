import type { DefaultSession } from "next-auth";

// Add the provider user id onto the session so server code (the BFF) can forward it.
declare module "next-auth" {
  interface Session {
    user: { id: string } & DefaultSession["user"];
  }
}

# Support Copilot — frontend

Next.js 16 (App Router) frontend for the multi-agent support assistant. Deploys to **Vercel**.

- **Auth:** Auth.js (NextAuth v5) with Google OAuth. Routes under `app/(protected)` are gated.
- **BFF proxy:** route handlers in `app/api/*` forward to the FastAPI backend with a shared secret +
  the signed-in user's identity, so the browser never calls the backend directly. See `lib/backend.ts`.
- **Styling:** Tailwind CSS v4 with a semantic token system in `app/globals.css` (light + dark).

## Develop

```bash
npm install
cp .env.example .env.local
npm run dev      # http://localhost:3000
npm run build    # production build
npm run lint
```

## Environment

| Var | Purpose |
| --- | --- |
| `BACKEND_URL` | FastAPI base URL (server-side only) |
| `SERVICE_SHARED_SECRET` | Shared secret sent to the backend; must match its `SERVICE_SHARED_SECRET` |
| `AUTH_SECRET` | Auth.js secret (`npx auth secret`) |
| `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET` | Google OAuth client credentials |
| `NEXT_PUBLIC_SITE_URL` | Public site URL for metadata/OG |

Google OAuth authorized redirect URI: `<site>/api/auth/callback/google`.

## Notes

- This is Next.js 16: middleware is replaced by `proxy`, and `params`/`headers`/`cookies` are async.
  Route protection here is done in the `app/(protected)/layout.tsx` server component instead of proxy.
- The bundled framework docs live in `node_modules/next/dist/docs/` — read them before changing
  framework-level conventions.

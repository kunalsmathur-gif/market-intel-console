# Citebell web app

Next.js 16 + Tailwind 4. It only reads and displays: no model calls and no data-provider keys (PRD §8.1). Deployed on Vercel with the project root set to `apps/web`.

```bash
cp .env.example .env.local   # Supabase URL and publishable key
npm install
npm run dev
```

- **Sign-in:** Supabase magic link, owner-only. `src/proxy.ts` refreshes the session and redirects signed-out visitors; pages still check the owner through the database's `is_owner()` function, and RLS enforces it on every table.
- **Supabase settings:** turn off public sign-ups, add `<site>/auth/confirm` to the redirect URLs, and add the owner's email to `public.allowed_users`.
- **Types:** `src/lib/schemas.generated.ts` comes from the Python models in `packages/schemas`. After changing them, run `python -m citebell_schemas.export packages/schemas/citebell.schema.json` from the repo root, then `npm run gen:types` here.
- **Design tokens:** `src/app/globals.css`, taken from `design-system/citebell/MASTER.md`.

`AGENTS.md` is written by `next dev`; it points coding agents at the Next.js docs bundled in `node_modules/next/dist/docs/`.

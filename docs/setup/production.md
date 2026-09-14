# Production setup (plan Task 0.3, Checkpoint A)

This guide takes Citebell from merged code to a running production setup:
- sign-in on Vercel, with the magic link and Google;
- the database on Supabase in Mumbai;
- the worker idling on Railway, with an uptime monitor.

**Before you start:**
- Merge PRs #1 → #2 → #3 → #4 on GitHub, in that order.
- Keep your password manager open.
- Enter every key and password only in the service dashboards. Never paste them into chat, commits or issues.
- Dashboard labels change from time to time. If a label doesn't match, look for the nearest equivalent.

Steps depend on each other in this order: **Supabase → Vercel → Supabase auth URLs → Google → uptime monitor → GitHub token → Railway**.

---

## 1. Supabase project

1. In the Supabase dashboard, create a **new project**:
   - Name: `citebell`.
   - Region: **South Asia (Mumbai)**.
   - Save the database password in your password manager.
2. Note these values; you'll need them in later steps:
   - **Project ref:** the part before `.supabase.co` in the project URL.
   - **Project URL:** `https://<project-ref>.supabase.co`.
   - **Publishable key:** Project Settings → API Keys, starts with `sb_publishable_`. It's safe for the web app; never use the secret key there.
   - **Session pooler connection string:** Project Settings → Database → Connection string → *Session pooler*, port 5432. Use the pooler, not the direct connection, because Railway may not reach IPv6-only hosts.

## 2. Apply the database schema

From the repo root on your PC (Node is already installed):

```bash
npx supabase login
```

```bash
npx supabase init --workdir infra
```

```bash
npx supabase link --project-ref <project-ref> --workdir infra
```

```bash
npx supabase db push --workdir infra
```

- `init` creates `infra/supabase/config.toml`. Answer "no" to the optional editor prompts, and leave the new files uncommitted; I'll tidy them in a later task.
- `link` asks for the database password from step 1.
- `db push` lists `20260914120000_init.sql`. Confirm to apply it.

**Check:** Table Editor shows tables such as `reports`, `claims` and `report_runs`, each marked RLS enabled.

## 3. Deploy the web app on Vercel

1. **Add New → Project** → import `kunalsmathur-gif/market-intel-console`.
2. **Root Directory:** `apps/web`. The framework preset is Next.js.
3. **Environment variables:**
   - `NEXT_PUBLIC_SUPABASE_URL` = the project URL.
   - `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` = the publishable key.
4. **Deploy.** Note the production domain, e.g. `https://<something>.vercel.app`.
5. **Region:** Project Settings → Functions → set the region to **Mumbai (bom1)** if your plan allows.

## 4. Supabase sign-in settings

1. **Authentication → URL Configuration:**
   - **Site URL:** `https://<vercel-domain>`.
   - **Redirect URLs:** add `https://<vercel-domain>/auth/confirm` and `http://localhost:3000/auth/confirm`.
2. **Authentication → Sign In / Providers:**
   - Turn **off** "Allow new users to sign up".
   - Keep the **Email** provider on; the magic link uses it.
3. **Authentication → Users → Add user → Create new user:**
   - **Email:** your email.
   - **Password:** a long random one from your password manager. It's never used; sign-in is by link or Google.
   - Tick **Auto Confirm User**.
4. **SQL Editor:** add yourself to the owner allowlist (lowercase email):

   ```sql
   insert into public.allowed_users (email) values (lower('you@example.com'));
   ```

Supabase's built-in email service sends only a few emails an hour. That's enough for one owner; a custom SMTP can come later.

## 5. Google OAuth client

1. In the **Google Cloud console**, create a project named `Citebell`.
2. **Google Auth Platform** (formerly "OAuth consent screen") → Get started:
   - App name: `Citebell`.
   - Support and contact email: yours.
   - Audience: **External**.
3. **Audience → Test users:** add your Google account. The app stays in *Testing*, so only listed accounts can even reach the consent screen.
4. **Clients → Create client:**
   - Application type: **Web application**, named `Citebell web`.
   - **Authorized JavaScript origins:** `https://<vercel-domain>`.
   - **Authorized redirect URIs:** `https://<project-ref>.supabase.co/auth/v1/callback`.
   - Create, then copy the **Client ID** and **Client secret** to your password manager right away.
5. Back in Supabase, **Authentication → Sign In / Providers → Google:** enable it, paste the client ID and secret, and save.

## 6. Uptime monitor

1. Create a free account on a cron-monitoring service, for example healthchecks.io.
2. **Add check:**
   - Name: `citebell-worker`.
   - **Period** 5 minutes, **grace** 10 minutes.
   - Alerts: email for now; Telegram arrives with the bot in Phase 1.
3. Copy the check's **ping URL**.

## 7. GitHub token for the private config

The worker downloads prompts and the source registry from `citebell-private` at startup.

1. **GitHub → Settings → Developer settings → Fine-grained personal access tokens → Generate new token.**
   - Name: `citebell-worker-config`.
   - Expiration: 90 days. Add a calendar reminder to rotate it.
   - Repository access: **Only select repositories** → `citebell-private`.
   - Permissions: **Contents: Read-only**. Metadata read-only is added automatically. Nothing else.
2. Copy the token to your password manager.
3. Copy the full **commit SHA** of the latest commit on `citebell-private` (Commits → copy). Production pins to it, so a prompt change reaches the worker only when you move the pin.

## 8. Deploy the worker on Railway

1. **New Project → Deploy from GitHub repo** → `kunalsmathur-gif/market-intel-console`.
2. **Service settings:**
   - Leave **Root Directory** empty (the repo root).
   - Set the **Railway config file** to `apps/worker/railway.json`. It builds `apps/worker/Dockerfile` and runs `citebell-worker scheduler`.
   - Choose the region nearest Mumbai.
3. **Variables:**

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Session pooler connection string, with the password filled in |
   | `PRIVATE_CONFIG_REPO` | `kunalsmathur-gif/citebell-private` |
   | `PRIVATE_CONFIG_REF` | The commit SHA from step 7 |
   | `PRIVATE_CONFIG_TOKEN` | The fine-grained token |
   | `HEALTHCHECK_PING_URL` | The ping URL from step 6 |

4. **Deploy.** Until the pipeline exists, scheduled runs finish as **withheld**. That's expected: nothing unverified can be published.

---

## Checkpoint A: verify

- [ ] **Magic link:**
  1. Open `https://<vercel-domain>` and request a link for your email.
  2. Open the link **in the same browser**.
  3. You land on **Today**, with four report cards reading "Not published yet".
- [ ] **Google:** sign out, then **Continue with Google** with your account → Today.
- [ ] **Other accounts:** a different Google account is refused, or sees "This account can't open Citebell".
- [ ] **Railway logs** show:
  - `private config: github kunalsmathur-gif/citebell-private@<sha> (35 sources)`
  - `scheduler started with 5 jobs`
  - no `ERROR` lines.
- [ ] **Uptime monitor:** the check is **up**, with a ping about every 5 minutes.
- [ ] **CI:** green on `main`.

When all six boxes are ticked, tell me "Checkpoint A done", without any keys, and we move to the Phase 1 spikes.

## Troubleshooting

| You see | Fix |
|---|---|
| Login page: "That sign-in link has expired or was already used" | Request a new link. Each link works once. |
| Login page: "Sign-in didn't complete. Start again in this browser" | Open the email link in the browser where you requested it. The secure sign-in flow is tied to that browser. |
| Google: `redirect_uri_mismatch` | The redirect URI in Google Cloud must be exactly `https://<project-ref>.supabase.co/auth/v1/callback`. |
| Your own Google account is refused although the magic link works | Tell me. Supabase should link Google to your existing account by email. If it doesn't with sign-ups off, we'll adjust the setting for a one-time link. |
| Railway: `PRIVATE_CONFIG_TOKEN was rejected` | The token expired or was revoked. Generate a new one (step 7) and update the variable. |
| Railway: `... not found, or PRIVATE_CONFIG_TOKEN can't read it` | Check the token's repository access (`citebell-private`) and the Contents: Read-only permission, and that the pinned SHA exists. |
| Railway: database connection errors | Use the **session pooler** string, check the password, and keep port 5432. |
| Railway: `another scheduler holds the lock; exiting` | Two replicas are running. Keep `numReplicas` at 1. |
| Uptime monitor goes down | Check the Railway service state and logs. The heartbeat also checks the database connection. |

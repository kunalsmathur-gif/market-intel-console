"""Reads a provider credential (e.g. Upstox's daily access token) that the owner pasted into
the web app's Settings page, instead of an environment variable that would need a redeploy
every trading day (PRD §8.5 broker connect, §9.3 daily login).

The worker connects to Postgres directly and bypasses row-level security (see the header of
`infra/supabase/migrations/*_init.sql`), so it can read a secret that only the owner may write
through the web app's `provider_credentials` RLS policies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import psycopg


class CredentialsError(RuntimeError):
    """No usable credential is stored for this provider: missing, or expired."""


@dataclass(frozen=True)
class Credential:
    provider: str
    access_token: str
    expires_at: datetime
    updated_at: datetime

    @property
    def expired(self) -> bool:
        return self.expires_at <= datetime.now(UTC)


def load_credential(conn: psycopg.Connection[Any], provider: str) -> Credential:
    """Fetch and validate today's credential, or raise with a message fit for an alert."""
    row = conn.execute(
        """
        select access_token, expires_at, updated_at
          from public.provider_credentials
         where provider = %s
        """,
        (provider,),
    ).fetchone()
    if row is None:
        raise CredentialsError(
            f"no {provider!r} credential saved yet — set it on the Settings page"
        )

    access_token, expires_at, updated_at = row
    credential = Credential(
        provider=provider, access_token=access_token, expires_at=expires_at, updated_at=updated_at
    )
    if credential.expired:
        raise CredentialsError(
            f"{provider!r} credential expired at {expires_at.isoformat()}"
            " — reconnect on the Settings page"
        )
    return credential

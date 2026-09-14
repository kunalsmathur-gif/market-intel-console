"""Download the private config repo from GitHub at a pinned commit (plan Task 0.3).

Only the files the worker reads are fetched, through the contents API with a read-only
fine-grained token. Recorded eval days in the same repo are never downloaded. Each commit is
cached in its own directory, so a restart at the same commit downloads nothing, and the commit
is reported so every run can say which prompts and sources it used.
"""

import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import EXAMPLE_PRIVATE_CONFIG, Settings
from .private_config import PrivateConfig, PrivateConfigError, load_private_config

API = "https://api.github.com"
FILES: tuple[tuple[str, bool], ...] = (("sources.toml", True), ("nse_holidays.txt", False))
DIRECTORIES = ("prompts",)

REPO_PATTERN = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
REF_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
FILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class FetchedConfig:
    root: Path
    repo: str
    commit: str

    def describe(self) -> str:
        return f"github {self.repo}@{self.commit[:12]}"


def load_configured_private_config(
    settings: Settings, client: httpx.Client | None = None
) -> tuple[PrivateConfig, str]:
    """Load the private config from wherever settings point. Returns the config and its source.

    Order: PRIVATE_CONFIG_DIR (a local checkout), then PRIVATE_CONFIG_REPO (downloaded from GitHub),
    then the public example, which is only good for tests and local runs.
    """
    if settings.private_config_dir is not None:
        return load_private_config(settings.private_config_dir), f"local {settings.private_config_dir}"
    if settings.private_config_repo:
        if settings.private_config_token is None:
            raise PrivateConfigError("PRIVATE_CONFIG_TOKEN is required with PRIVATE_CONFIG_REPO")
        http = client or httpx.Client(timeout=30)
        try:
            fetched = fetch_private_config(
                settings.private_config_repo,
                settings.private_config_ref,
                settings.private_config_token.get_secret_value(),
                settings.private_config_cache_dir,
                http,
            )
        finally:
            if client is None:
                http.close()
        return load_private_config(fetched.root), fetched.describe()
    return load_private_config(EXAMPLE_PRIVATE_CONFIG), "public example (tests and local runs only)"


def fetch_private_config(
    repo: str, ref: str, token: str, cache_root: Path, client: httpx.Client
) -> FetchedConfig:
    if not REPO_PATTERN.match(repo):
        raise PrivateConfigError(f"PRIVATE_CONFIG_REPO must look like owner/name, got {repo!r}")
    if not REF_PATTERN.match(ref) or ".." in ref:
        raise PrivateConfigError(f"PRIVATE_CONFIG_REF is not a valid branch, tag or commit: {ref!r}")
    headers = {"Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"}

    commit = _resolve_commit(client, repo, ref, headers)
    target = cache_root / commit
    if (target / "sources.toml").is_file():
        return FetchedConfig(target, repo, commit)

    cache_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{commit[:12]}-", dir=cache_root))
    try:
        for name, required in FILES:
            content = _file(client, repo, name, commit, headers, required)
            if content is not None:
                (staging / name).write_bytes(content)
        for directory in DIRECTORIES:
            (staging / directory).mkdir()
            for name in _file_names(client, repo, directory, commit, headers):
                content = _file(client, repo, f"{directory}/{name}", commit, headers, required=True)
                assert content is not None
                (staging / directory / name).write_bytes(content)
        try:
            staging.rename(target)
        except OSError:
            if not (target / "sources.toml").is_file():
                raise
            shutil.rmtree(staging, ignore_errors=True)  # another process cached this commit first
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return FetchedConfig(target, repo, commit)


def _resolve_commit(client: httpx.Client, repo: str, ref: str, headers: dict[str, str]) -> str:
    response = _get(client, f"{API}/repos/{repo}/commits/{ref}",
                    headers | {"Accept": "application/vnd.github.sha"})
    if response.status_code == 200:
        sha = response.text.strip()
        if SHA_PATTERN.match(sha):
            return sha
        raise PrivateConfigError(f"GitHub returned an unexpected commit id for {repo}@{ref}")
    raise _error(response, repo, f"ref {ref!r}")


def _file(
    client: httpx.Client, repo: str, path: str, commit: str, headers: dict[str, str], required: bool
) -> bytes | None:
    response = _get(client, f"{API}/repos/{repo}/contents/{path}", headers | {
        "Accept": "application/vnd.github.raw+json"}, params={"ref": commit})
    if response.status_code == 200:
        return response.content
    if response.status_code == 404 and not required:
        return None
    raise _error(response, repo, path)


def _file_names(
    client: httpx.Client, repo: str, directory: str, commit: str, headers: dict[str, str]
) -> list[str]:
    response = _get(client, f"{API}/repos/{repo}/contents/{directory}", headers | {
        "Accept": "application/vnd.github+json"}, params={"ref": commit})
    if response.status_code == 404:
        return []
    if response.status_code != 200:
        raise _error(response, repo, directory)
    entries: list[dict[str, Any]] = response.json()
    names = []
    for entry in entries:
        if entry.get("type") != "file":
            continue
        name = str(entry.get("name", ""))
        if not FILE_NAME_PATTERN.match(name):
            raise PrivateConfigError(f"unsafe file name in {repo}/{directory}: {name!r}")
        names.append(name)
    return names


def _get(
    client: httpx.Client, url: str, headers: dict[str, str], params: dict[str, str] | None = None
) -> httpx.Response:
    try:
        return client.get(url, headers=headers, params=params)
    except httpx.HTTPError as exc:
        raise PrivateConfigError(f"cannot reach GitHub for the private config: {exc}") from exc


def _error(response: httpx.Response, repo: str, what: str) -> PrivateConfigError:
    if response.status_code == 401:
        return PrivateConfigError("PRIVATE_CONFIG_TOKEN was rejected: it may have expired or been revoked")
    if response.status_code in (403, 404):
        return PrivateConfigError(
            f"{repo}: {what} not found, or PRIVATE_CONFIG_TOKEN can't read it "
            "(the token needs read-only Contents access to this repo)"
        )
    if response.status_code == 422:
        return PrivateConfigError(f"{repo}: {what} doesn't exist")
    return PrivateConfigError(f"{repo}: GitHub answered HTTP {response.status_code} for {what}")

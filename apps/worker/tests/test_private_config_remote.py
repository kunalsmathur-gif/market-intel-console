from pathlib import Path

import httpx
import pytest
import respx
from pydantic import SecretStr

from citebell_worker.config import Settings
from citebell_worker.private_config import PrivateConfigError
from citebell_worker.private_config_remote import fetch_private_config, load_configured_private_config

REPO = "owner/citebell-private"
SHA = "a" * 40
API = "https://api.github.com/repos/owner/citebell-private"
SOURCES = b'[[source]]\nid = "rbi"\nname = "RBI"\ndomain = "rbi.org.in"\ntier = "T1"\nkind = "rss"\n'


def mock_repo(prompts: list[dict[str, str]] | None = None, holidays: int = 200) -> respx.Route:
    commit = respx.get(f"{API}/commits/main").mock(return_value=httpx.Response(200, text=SHA))
    respx.get(f"{API}/contents/sources.toml", params={"ref": SHA}).mock(
        return_value=httpx.Response(200, content=SOURCES))
    respx.get(f"{API}/contents/nse_holidays.txt", params={"ref": SHA}).mock(
        return_value=httpx.Response(holidays, content=b"2026-10-02\n"))
    listing = prompts if prompts is not None else [
        {"type": "file", "name": "extract.md"}, {"type": "dir", "name": "drafts"}]
    respx.get(f"{API}/contents/prompts", params={"ref": SHA}).mock(
        return_value=httpx.Response(200, json=listing))
    respx.get(f"{API}/contents/prompts/extract.md", params={"ref": SHA}).mock(
        return_value=httpx.Response(200, content=b"Never write a number."))
    return commit


def fetch(tmp_path: Path) -> Path:
    with httpx.Client() as client:
        return fetch_private_config(REPO, "main", "token", tmp_path, client).root


@respx.mock
def test_downloads_only_the_config_files_at_the_resolved_commit(tmp_path: Path) -> None:
    commit = mock_repo()
    root = fetch(tmp_path)
    assert root == tmp_path / SHA
    assert (root / "sources.toml").read_bytes() == SOURCES
    assert (root / "prompts" / "extract.md").read_text() == "Never write a number."
    assert not (root / "prompts" / "drafts").exists()  # subdirectories are skipped
    assert commit.calls.last.request.headers["Authorization"] == "Bearer token"


@respx.mock
def test_a_cached_commit_is_not_downloaded_again(tmp_path: Path) -> None:
    mock_repo()
    fetch(tmp_path)
    contents = respx.get(f"{API}/contents/sources.toml", params={"ref": SHA})  # the route already mocked
    downloads = contents.call_count
    fetch(tmp_path)
    assert contents.call_count == downloads == 1


@respx.mock
def test_optional_files_may_be_missing(tmp_path: Path) -> None:
    mock_repo(holidays=404)
    assert not (fetch(tmp_path) / "nse_holidays.txt").exists()


@pytest.mark.parametrize(
    ("status", "message"),
    [(401, "was rejected"), (404, "can't read it"), (422, "doesn't exist")],
)
@respx.mock
def test_commit_lookup_errors_explain_the_fix(tmp_path: Path, status: int, message: str) -> None:
    respx.get(f"{API}/commits/main").mock(return_value=httpx.Response(status))
    with pytest.raises(PrivateConfigError, match=message):
        fetch(tmp_path)


@respx.mock
def test_missing_sources_file_fails_and_leaves_no_partial_cache(tmp_path: Path) -> None:
    mock_repo()
    respx.get(f"{API}/contents/sources.toml", params={"ref": SHA}).mock(return_value=httpx.Response(404))
    with pytest.raises(PrivateConfigError):
        fetch(tmp_path)
    assert list(tmp_path.iterdir()) == []


@respx.mock
def test_unsafe_file_names_are_rejected(tmp_path: Path) -> None:
    mock_repo(prompts=[{"type": "file", "name": "../escape.md"}])
    with pytest.raises(PrivateConfigError, match="unsafe file name"):
        fetch(tmp_path)


@pytest.mark.parametrize(("repo", "ref"), [("not-a-repo", "main"), (REPO, "../main"), (REPO, "main;rm")])
def test_bad_repo_or_ref_is_rejected_before_any_request(tmp_path: Path, repo: str, ref: str) -> None:
    with httpx.Client() as client, pytest.raises(PrivateConfigError):
        fetch_private_config(repo, ref, "token", tmp_path, client)


def test_blank_values_copied_from_env_example_count_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("PRIVATE_CONFIG_DIR", "PRIVATE_CONFIG_REPO", "PRIVATE_CONFIG_TOKEN", "HEALTHCHECK_PING_URL"):
        monkeypatch.setenv(name, "")
    settings = Settings(_env_file=None)
    assert settings.private_config_dir is None
    assert settings.private_config_token is None
    assert load_configured_private_config(settings)[1].startswith("public example")


def test_settings_choose_local_then_github_then_example(tmp_path: Path) -> None:
    config, source = load_configured_private_config(Settings.model_validate({}))
    assert source.startswith("public example")
    assert config.sources

    with pytest.raises(PrivateConfigError, match="PRIVATE_CONFIG_TOKEN is required"):
        load_configured_private_config(Settings.model_validate({"private_config_repo": REPO}))

    with respx.mock:
        mock_repo()
        settings = Settings.model_validate({
            "private_config_repo": REPO, "private_config_token": SecretStr("token"),
            "private_config_cache_dir": tmp_path})
        config, source = load_configured_private_config(settings)
    assert source == f"github {REPO}@{SHA[:12]}"
    assert [s.id for s in config.sources] == ["rbi"]

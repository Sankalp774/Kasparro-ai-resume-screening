"""Public GitHub is a witness. A failed call scores 0 and the batch continues."""

import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from src.config import GITHUB_CAP, GITHUB_RECENT_DAYS, GITHUB_REPO_DAYS
from src.eligibility import ai_terms
from src.models import GitHubResult

MISSING_SUMMARY = "No GitHub profile on resume"


class GitHubHTTPError(Exception):
    def __init__(self, code: int, url: str):
        super().__init__(f"HTTP {code} for {url}")
        self.code = code
        self.url = url


def http_get_json(url: str, token: str | None, timeout: float = 10.0) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "resume-screener",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise GitHubHTTPError(exc.code, url) from exc
    except urllib.error.URLError as exc:
        raise GitHubHTTPError(0, url) from exc


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _activity_points(push_count: int) -> int:
    if push_count >= 10:
        return 5
    if push_count >= 3:
        return 4
    if push_count >= 1:
        return 2
    return 0


def _repo_points(repo_count: int) -> int:
    if repo_count >= 4:
        return 5
    if repo_count >= 2:
        return 4
    if repo_count >= 1:
        return 2
    return 0


def _repo_is_relevant(repo: dict) -> bool:
    language = str(repo.get("language") or "")
    blob = f"{repo.get('name') or ''} {repo.get('description') or ''}"
    return language.lower() == "python" or bool(ai_terms(blob))


class GitHubEnricher:
    def __init__(self, token: str | None = None, getter=None, now: datetime | None = None):
        self._getter = getter or (lambda url: http_get_json(url, token))
        self._now = now or datetime.now(timezone.utc)
        self.cache: dict[str, GitHubResult] = {}

    def enrich(self, username: str | None) -> GitHubResult:
        if not username:
            return GitHubResult(points=0, status="missing", summary=MISSING_SUMMARY)
        key = username.lower()
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        result = self._fetch(username)
        self.cache[key] = result
        return result

    def _fetch(self, username: str) -> GitHubResult:
        safe = quote(username)
        repos_url = f"https://api.github.com/users/{safe}/repos?per_page=100&sort=updated"
        events_url = f"https://api.github.com/users/{safe}/events/public?per_page=100"
        try:
            repos = self._getter(repos_url)
            events = self._getter(events_url)
        except GitHubHTTPError as exc:
            return GitHubResult(
                points=0,
                status="failed",
                summary=f"GitHub enrichment failed (HTTP {exc.code}). Score left at 0.",
            )
        except Exception as exc:
            return GitHubResult(
                points=0,
                status="failed",
                summary=f"GitHub enrichment failed ({type(exc).__name__}). Score left at 0.",
            )

        if not isinstance(repos, list) or not isinstance(events, list):
            return GitHubResult(
                points=0,
                status="failed",
                summary="GitHub enrichment failed (unexpected response). Score left at 0.",
            )

        recent_cutoff = self._now - timedelta(days=GITHUB_RECENT_DAYS)
        repo_cutoff = self._now - timedelta(days=GITHUB_REPO_DAYS)
        pushes = 0
        for event in events:
            if not isinstance(event, dict) or event.get("type") != "PushEvent":
                continue
            created = _parse_time(event.get("created_at"))
            if created is not None and created >= recent_cutoff:
                pushes += 1

        relevant = 0
        for repo in repos:
            if not isinstance(repo, dict) or repo.get("fork"):
                continue
            updated = _parse_time(repo.get("pushed_at") or repo.get("updated_at"))
            if updated is None or updated < repo_cutoff:
                continue
            if _repo_is_relevant(repo):
                relevant += 1

        activity = _activity_points(pushes)
        maintained = _repo_points(relevant)
        points = min(GITHUB_CAP, activity + maintained)
        summary = (
            f"{pushes} push events in the last {GITHUB_RECENT_DAYS} days (+{activity}), "
            f"{relevant} relevant public repos updated in {GITHUB_REPO_DAYS} days (+{maintained})."
        )
        return GitHubResult(points=points, status="ok", summary=summary)

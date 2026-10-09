from datetime import datetime, timezone

from src.extract import extract_text
from src.github_enrich import MISSING_SUMMARY, GitHubEnricher, GitHubHTTPError

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def _payload(url: str):
    if "events" in url:
        return [
            {"type": "PushEvent", "created_at": "2026-09-01T00:00:00Z"},
            {"type": "PushEvent", "created_at": "2026-09-02T00:00:00Z"},
            {"type": "WatchEvent", "created_at": "2026-09-03T00:00:00Z"},
        ]
    return [
        {
            "name": "rag-agent",
            "language": "Python",
            "pushed_at": "2026-08-01T00:00:00Z",
            "fork": False,
            "description": "langgraph rag",
        }
    ]


def test_same_username_is_fetched_once():
    calls: list[str] = []

    def getter(url: str):
        calls.append(url)
        return _payload(url)

    enricher = GitHubEnricher(getter=getter, now=NOW)
    first = enricher.enrich("Octocat")
    second = enricher.enrich("octocat")
    assert first.points == second.points
    assert first.points > 0
    assert len(calls) == 2


def test_http_404_scores_zero_and_records_failure():
    def getter(url: str):
        raise GitHubHTTPError(404, url)

    result = GitHubEnricher(getter=getter, now=NOW).enrich("missing-user")
    assert result.points == 0
    assert result.status == "failed"
    assert "404" in result.summary


def test_github_label_without_a_profile_url_is_missing():
    resume = extract_text("Skills\nPython GitHub\nProjects\nBuilt a LangGraph agent.", "a.pdf")
    assert resume.github_username is None
    result = GitHubEnricher(getter=lambda url: [], now=NOW).enrich(resume.github_username)
    assert result.points == 0
    assert result.summary == MISSING_SUMMARY

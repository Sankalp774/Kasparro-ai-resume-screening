"""Normalize resume text and pull name, email, sections, and GitHub."""

import re

from src.models import ExtractedResume

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
GITHUB_RE = re.compile(r"github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))", re.I)
GITHUB_RESERVED = {
    "orgs",
    "features",
    "topics",
    "marketplace",
    "apps",
    "settings",
    "sponsors",
    "collections",
    "about",
    "site",
    "github",
    "pulls",
    "issues",
    "blob",
    "tree",
    "commit",
    "commits",
}

_HEADINGS = {
    "skills": "skills",
    "technicalskills": "skills",
    "corecompetencies": "skills",
    "techstack": "skills",
    "technicalstack": "skills",
    "projects": "projects",
    "keyprojects": "projects",
    "personalprojects": "projects",
    "academicprojects": "projects",
    "projectexperience": "projects",
    "experience": "work",
    "workexperience": "work",
    "professionalexperience": "work",
    "internship": "work",
    "internships": "work",
    "employment": "work",
}

_ROLE_WORDS = {
    "developer",
    "engineer",
    "intern",
    "manager",
    "student",
    "fresher",
    "analyst",
    "consultant",
    "trainee",
    "summary",
    "objective",
    "objectives",
    "profile",
    "education",
    "skills",
    "projects",
    "experience",
    "university",
    "college",
    "institute",
    "school",
    "academy",
    "languages",
    "language",
    "programming",
    "development",
    "github",
    "linkedin",
    "html",
    "css",
    "python",
    "java",
    "react",
    "native",
    "basic",
    "database",
    "visual",
    "studio",
    "jupyter",
    "google",
}


def _separate_glued_email(text: str) -> str:
    """Split 'Shaiksultanasumaiya623@gmail.com' when a prior name word repeats."""

    def fix_line(line: str) -> str:
        at_index = line.find("@")
        if at_index == -1:
            return line
        start = at_index
        while start > 0 and re.match(r"[A-Za-z0-9._%+-]", line[start - 1]):
            start -= 1
        local = line[start:at_index]
        if not re.search(r"\d", local):
            return line
        prior_words = re.findall(r"[A-Za-z]{4,}", line[:start])
        local_lower = local.lower()
        splits = [
            local_lower.find(word.lower())
            for word in prior_words
            if local_lower.find(word.lower()) > 0
        ]
        split_at = min(splits) if splits else None
        if split_at is None:
            return line
        return f"{line[:start]}{local[:split_at]} {local[split_at:]}{line[at_index:]}"

    return "\n".join(fix_line(line) for line in text.splitlines())


def normalize(text: str) -> str:
    """Collapse layout noise from PDF extraction without splitting camel-case tokens."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # "inReact" -> "in React". Do not split AbhinavMishra or FastAPI.
    text = re.sub(r"\b(in|with|and|the|for|using|via|on)(?=[A-Z])", r"\1 ", text)
    text = re.sub(r"(?<=[A-Za-z])(?=Email\s*:)", " ", text)
    text = _separate_glued_email(text)
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _classify_heading(line: str) -> str | None:
    raw = line.strip()
    if not raw or len(raw) > 40:
        return None
    if len(raw.split()) > 4:
        return None
    compact = re.sub(r"[^A-Za-z]", "", raw).lower()
    return _HEADINGS.get(compact)


def _split_sections(text: str) -> tuple[str, str, str]:
    buckets: dict[str, list[str]] = {"skills": [], "projects": [], "work": []}
    current: str | None = None
    for line in text.splitlines():
        kind = _classify_heading(line)
        if kind:
            current = kind
            continue
        if current:
            buckets[current].append(line)
    return (
        "\n".join(buckets["skills"]).strip(),
        "\n".join(buckets["projects"]).strip(),
        "\n".join(buckets["work"]).strip(),
    )


def _looks_like_name(line: str) -> bool:
    raw = line.strip(" |-–—")
    if not raw or len(raw) > 40 or "@" in raw or "http" in raw.lower():
        return False
    if re.search(r"\d|[:]", raw):
        return False
    if re.search(r"(?i)linkedin|github|git hub|university|college|institute", raw):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z.'-]*", raw)
    if not 2 <= len(words) <= 5:
        return False
    if any(word.lower().strip(".") in _ROLE_WORDS for word in words):
        return False
    capitals = sum(1 for word in words if word[0].isupper())
    return capitals == len(words)


def _clean_name(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip(" |-–—")


def _skip_or_stop(line: str, parts: list[str]) -> str | None:
    """Return 'take', 'skip', or 'stop' for one header line."""
    raw = line.strip()
    if not raw:
        return "skip"
    if re.search(r"\d|@|http|[,|!:]", raw, re.I):
        return "stop" if parts else "skip"
    compact = re.sub(r"[^A-Za-z]", "", raw).lower()
    if compact in _HEADINGS or compact in {"summary", "professionalsummary", "objective", "objectives", "profile"}:
        return "skip"
    if re.search(r"(?i)linkedin|github|git hub|get in touch|phone|email|mobile", raw):
        return "stop" if parts else "skip"
    words = re.findall(r"[A-Za-z][A-Za-z.'-]*", raw)
    if not words or len(words) > 4:
        return "stop" if parts else "skip"
    if any(word.lower().strip(".") in _ROLE_WORDS for word in words):
        return "stop" if parts else "skip"
    if not all(word[0].isupper() for word in words):
        return "stop" if parts else "skip"
    return "take"


def _opening_name(lines: list[str]) -> str | None:
    parts: list[str] = []
    for line in lines[:10]:
        if "," in line and not parts:
            before = re.sub(r"([a-z])([A-Z])", r"\1 \2", line.split(",")[0])
            if _looks_like_name(before):
                return _clean_name(before)
        action = _skip_or_stop(line, parts)
        if action == "skip":
            continue
        if action == "stop":
            break
        words = re.findall(r"[A-Za-z][A-Za-z.'-]*", line)
        # A city often sits on the next line after a two-word name. Do not absorb it.
        if len(parts) >= 2 and len(words) == 1 and len(words[0]) > 1:
            break
        parts.extend(words)
        if len(parts) >= 2 and len(words) >= 2:
            break
        if len(parts) >= 4:
            break
    if len(parts) >= 2:
        return " ".join(parts[:5])
    return None


def _name_before_email(lines: list[str]) -> str | None:
    for line in lines:
        marker = re.search(r"(?i)\bemail\s*:", line)
        cut = marker.start() if marker else None
        if cut is None and "@" in line and "," not in line and "|" not in line:
            cut = line.find("@")
            # Keep the capitalized words and drop the local-part token.
            cut = line.rfind(" ", 0, cut)
            if cut == -1:
                continue
        if cut is None:
            continue
        before = line[:cut].strip(" |-–—")
        before = re.sub(r"([a-z])([A-Z])", r"\1 \2", before)
        before = before.split(",")[0].strip()
        if _looks_like_name(before):
            return _clean_name(before)
    return None


def _pick_name(lines: list[str]) -> str | None:
    glued = _name_before_email(lines)
    if glued:
        return glued
    opening = _opening_name(lines)
    if opening:
        return opening

    email_index = next((i for i, line in enumerate(lines) if EMAIL_RE.search(line)), None)
    if email_index is not None:
        window = lines[max(0, email_index - 8) : email_index]
        for line in reversed(window):
            if _looks_like_name(line) and not re.search(r"(?i)linkedin|github|touch", line):
                return _clean_name(line)

    for line in lines[:20]:
        if _looks_like_name(line) and not re.search(r"(?i)linkedin|github|touch", line):
            return _clean_name(line)
    return None


def _pick_github(text: str) -> tuple[str | None, str | None]:
    for match in GITHUB_RE.finditer(text):
        username = match.group(1)
        if username.lower() in GITHUB_RESERVED:
            continue
        url = f"https://github.com/{username}"
        return url, username
    return None, None


def extract_text(text: str, filename: str) -> ExtractedResume:
    normalized = normalize(text or "")
    skills, projects, work = _split_sections(normalized)
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    email_match = EMAIL_RE.search(normalized)
    github_url, github_username = _pick_github(normalized)
    return ExtractedResume(
        filename=filename,
        name=_pick_name(lines),
        email=email_match.group(0) if email_match else None,
        github_url=github_url,
        github_username=github_username,
        skills_text=skills,
        project_text=projects,
        work_text=work,
        full_text=normalized,
    )

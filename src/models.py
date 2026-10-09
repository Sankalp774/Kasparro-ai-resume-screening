"""Schemas for resumes, scores, and the witness judgment."""

from pydantic import BaseModel, Field

from src.config import AI_ADJUSTMENT_MAX, AI_ADJUSTMENT_MIN


class IngestedFile(BaseModel):
    filename: str
    text: str = ""
    status: str
    error: str | None = None
    duplicate_of: str | None = None


class ExtractedResume(BaseModel):
    filename: str
    name: str | None = None
    email: str | None = None
    github_url: str | None = None
    github_username: str | None = None
    skills_text: str = ""
    project_text: str = ""
    work_text: str = ""
    full_text: str = ""


class Eligibility(BaseModel):
    eligible: bool
    rejection_reasons: list[str] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)


class ScoreCard(BaseModel):
    ai_project_depth: int = 0
    python_backend: int = 0
    cloud_fullstack: int = 0
    github: int = 0
    engineering_depth: int = 0
    evidence: dict[str, str] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    project_summary: str = ""

    def total(self) -> int:
        raw = (
            self.ai_project_depth
            + self.python_backend
            + self.cloud_fullstack
            + self.github
            + self.engineering_depth
        )
        return max(0, min(100, raw))

    def breakdown(self) -> dict[str, int]:
        return {
            "ai_project_depth": self.ai_project_depth,
            "python_backend": self.python_backend,
            "cloud_fullstack": self.cloud_fullstack,
            "github": self.github,
            "engineering_depth": self.engineering_depth,
        }


class WitnessJudgment(BaseModel):
    """Testimony only. The pipeline decides whether to admit it."""

    ai_depth_adjustment: int = Field(ge=AI_ADJUSTMENT_MIN, le=AI_ADJUSTMENT_MAX)
    thin_wrapper: bool
    project_summary: str
    strengths: list[str]
    concerns: list[str]
    evidence_quote: str
    suggested_name: str = ""
    suggested_email: str = ""
    suggested_skills: list[str] = Field(default_factory=list)


class GitHubResult(BaseModel):
    points: int = 0
    status: str
    summary: str

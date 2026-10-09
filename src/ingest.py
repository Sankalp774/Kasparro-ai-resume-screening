"""Read a folder of PDFs. One bad file does not stop the batch."""

import hashlib
from pathlib import Path

from pypdf import PdfReader

from src.models import IngestedFile


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path), strict=False)
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def ingest_folder(input_dir: str) -> list[IngestedFile]:
    root = Path(input_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    files = sorted(
        path for path in root.iterdir() if path.is_file() and not path.name.startswith(".")
    )
    seen: dict[str, str] = {}
    documents: list[IngestedFile] = []

    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            documents.append(
                IngestedFile(
                    filename=path.name,
                    status="duplicate",
                    error=f"Duplicate of {seen[digest]}",
                    duplicate_of=seen[digest],
                )
            )
            continue
        seen[digest] = path.name

        if path.suffix.lower() != ".pdf":
            documents.append(
                IngestedFile(
                    filename=path.name,
                    status="failed",
                    error="Unsupported file type. This run reads PDF resumes.",
                )
            )
            continue

        try:
            text = _read_pdf(path)
        except Exception as exc:
            documents.append(
                IngestedFile(
                    filename=path.name,
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue

        documents.append(IngestedFile(filename=path.name, text=text, status="parsed"))

    return documents

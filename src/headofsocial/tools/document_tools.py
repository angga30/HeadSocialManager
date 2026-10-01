"""Tools to ingest uploaded documents (PDF/DOCX/MD/TXT) into text for the Positioning Agent."""

from pathlib import Path

from headofsocial.config import settings


def extract_text(path: Path) -> str:
    """Extract text from a supported document type; returns '' for unsupported files."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        from docx import Document

        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    if suffix in (".md", ".txt", ".text"):
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


async def read_document(filename: str, max_chars: int = 20000) -> dict:
    """Read an uploaded document from data/docs and return its text for analyzing.

    Args:
        filename: Name of the file in the data/docs folder (e.g. company-profile.pdf).
        max_chars: Limit on how much text to return (to protect context window).
    """
    base = settings.resolved_data_dir / "docs"
    path = base / filename
    if not path.exists():
        return {"ok": False, "error": f"File not found in {base}: {filename}"}
    text = extract_text(path)
    if not text.strip():
        return {
            "ok": False,
            "error": "Could not extract text (unsupported or empty file). Try PDF/DOCX/MD/TXT.",
        }
    return {"ok": True, "filename": filename, "text": text[:max_chars], "truncated": len(text) > max_chars}


async def list_documents() -> dict:
    """List available uploaded documents in data/docs."""
    base = settings.resolved_data_dir / "docs"
    base.mkdir(parents=True, exist_ok=True)
    files = sorted(p.name for p in base.iterdir() if p.is_file())
    return {"ok": True, "documents": files}
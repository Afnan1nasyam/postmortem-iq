"""Document loader: reads MD/TXT/HTML postmortems into a normalized plain-text form."""

import re
from pathlib import Path

from bs4 import BeautifulSoup
from loguru import logger

from src.models.schemas import PostmortemDocument

_SUPPORTED_EXTENSIONS = {".md", ".txt", ".html"}
_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _read_md(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    raw = _FRONTMATTER_RE.sub("", raw)
    return _normalize_whitespace(raw)


def _read_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator="\n")
    return _normalize_whitespace(text)


def _read_txt(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    return _normalize_whitespace(raw)


_READERS = {
    ".md": _read_md,
    ".txt": _read_txt,
    ".html": _read_html,
}


def load_document(file_path: Path) -> PostmortemDocument:
    """Load a postmortem file and return a PostmortemDocument with normalized text."""
    ext = file_path.suffix.lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {ext} (supported: {_SUPPORTED_EXTENSIONS})")

    text = _READERS[ext](file_path)

    if not text:
        logger.warning("Empty content after processing: {}", file_path)

    file_type = ext.lstrip(".")
    logger.info("Loaded {} ({} chars) from {}", file_type, len(text), file_path.name)

    return PostmortemDocument(
        file_path=str(file_path),
        file_type=file_type,
        raw_text=text,
    )

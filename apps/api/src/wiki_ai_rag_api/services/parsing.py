from __future__ import annotations

from pathlib import Path


def parse_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt", ".csv", ".json"}:
        return _read_text(path)
    if suffix == ".html":
        return _parse_html(path)
    if suffix == ".pdf":
        return _parse_pdf(path)
    if suffix == ".docx":
        return _parse_docx(path)
    raise ValueError(f"Unsupported file extension: {suffix}")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1251")


def _parse_html(path: Path) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(_read_text(path), "html.parser")
    return soup.get_text("\n")


def _parse_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _parse_docx(path: Path) -> str:
    from docx import Document

    document = Document(str(path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)

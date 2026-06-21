from pathlib import Path

import pytest

from wiki_ai_rag_api.services.parsing import parse_file


def test_parse_markdown_file(tmp_path: Path) -> None:
    path = tmp_path / "product.md"
    path.write_text("# Product X\n\nMarkdown knowledge.", encoding="utf-8")

    assert "Markdown knowledge" in parse_file(path)


def test_parse_txt_file_with_cp1251_fallback(tmp_path: Path) -> None:
    path = tmp_path / "ru.txt"
    path.write_bytes("Продукт X поддерживает импорт.".encode("cp1251"))

    assert "Продукт X" in parse_file(path)


def test_parse_docx_file(tmp_path: Path) -> None:
    pytest.importorskip("docx")
    from docx import Document

    path = tmp_path / "product.docx"
    document = Document()
    document.add_paragraph("Product X DOCX text.")
    document.save(path)

    assert "Product X DOCX text" in parse_file(path)


def test_parse_pdf_file(tmp_path: Path) -> None:
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    path = tmp_path / "product.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 24 Tf 100 700 Td (Product X PDF text) Tj ET")
    stream_ref = writer._add_object(stream)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )
    page[NameObject("/Contents")] = stream_ref
    with path.open("wb") as pdf_file:
        writer.write(pdf_file)

    assert "Product X PDF text" in parse_file(path)


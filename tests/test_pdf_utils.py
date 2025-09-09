from audit_lib.pdf_utils import pdf_to_text_with_page_markers, split_pages
from pypdf import PdfWriter


def test_pdf_to_text_with_page_markers_and_split(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    with pdf_path.open("wb") as f:
        writer.write(f)

    text = pdf_to_text_with_page_markers(str(pdf_path))
    assert "<<<PAGE=1>>>" in text
    assert "<<<PAGE=2>>>" in text

    pages = split_pages(text)
    assert pages[1] == ""
    assert pages[2] == ""

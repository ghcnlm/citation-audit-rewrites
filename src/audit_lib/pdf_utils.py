from typing import Dict
from pypdf import PdfReader


def pdf_to_text_with_page_markers(pdf_path: str) -> str:
    """Extract text from a PDF, inserting page markers.

    Parameters
    ----------
    pdf_path: str
        Path to the PDF file to read.

    Returns
    -------
    str
        Text of the PDF with markers of the form ``<<<PAGE=n>>>`` before each
        page's content.

    Raises
    ------
    FileNotFoundError
        If ``pdf_path`` does not exist.
    PdfReadError
        Propagated from :class:`pypdf.PdfReader` when the file cannot be read.
    """

    reader = PdfReader(pdf_path)
    out_lines: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        out_lines.append(f"<<<PAGE={i}>>>")
        text = page.extract_text() or ""
        out_lines.append(text.strip())
    return "\n".join(out_lines)


def split_pages(text_with_markers: str) -> Dict[int, str]:
    """Split page-marked text back into individual pages.

    Parameters
    ----------
    text_with_markers: str
        Text produced by :func:`pdf_to_text_with_page_markers`.

    Returns
    -------
    Dict[int, str]
        Mapping of page numbers to their text content.

    Notes
    -----
    Lines without page markers are associated with the current page. No
    exceptions are raised unless the input format is malformed.
    """

    pages: Dict[int, str] = {}
    current_page: int | None = None
    buf: list[str] = []
    for line in text_with_markers.splitlines():
        if line.startswith("<<<PAGE=") and line.endswith(">>>"):
            if current_page is not None:
                pages[current_page] = "\n".join(buf).strip()
                buf = []
            current_page = int(line.replace("<<<PAGE=", "").replace(">>>", ""))
        else:
            buf.append(line)
    if current_page is not None:
        pages[current_page] = "\n".join(buf).strip()
    return pages

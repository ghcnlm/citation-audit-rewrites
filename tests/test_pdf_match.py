from pathlib import Path

from audit_lib.enrich.pdf_match import (
    infer_year_for_target_author,
    build_pdf_index,
    resolve_pdf_path,
)


def test_infer_year_for_target_author_multi() -> None:
    citation_author = "Chirau et al."
    citation_text = "(Chirau et al., 2022; Kanyamuna et al., 2018)"
    assert infer_year_for_target_author(citation_author, citation_text) == "2022"


def test_resolve_pdf_path_multi_citation(tmp_path: Path) -> None:
    (tmp_path / "Chirau_2022.pdf").write_bytes(b"")
    (tmp_path / "Kanyamuna_2018.pdf").write_bytes(b"")
    index = build_pdf_index(tmp_path)
    row = {
        "citation_author": "Chirau et al.",
        "citation_text": "(Chirau et al., 2022; Kanyamuna et al., 2018)",
        "citation_year": "",
    }
    resolved = resolve_pdf_path(row, index)
    assert resolved and resolved.name == "Chirau_2022.pdf"

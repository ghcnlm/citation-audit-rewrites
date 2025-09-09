from pathlib import Path

from audit_lib.pdf_map import (
    normalize_lead_surname,
    build_pdf_index,
    resolve_source_pdf,
)


def touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1.4\n% test file\n")


def test_exact_year_match(tmp_path: Path):
    # Arrange: two Johnson PDFs with different years
    touch(tmp_path / "Johnson_1998.pdf")
    touch(tmp_path / "Johnson_2009.pdf")
    index = build_pdf_index(tmp_path)

    # Act
    res_2009 = resolve_source_pdf("Johnson et al.", 2009, index)
    res_1998 = resolve_source_pdf("Johnson", 1998, index)

    # Assert
    assert res_2009.path and res_2009.path.name == "Johnson_2009.pdf"
    assert res_1998.path and res_1998.path.name == "Johnson_1998.pdf"


def test_no_cross_year_fallback(tmp_path: Path):
    # Only 1998 exists; ask for 2009 should yield None
    touch(tmp_path / "Johnson_1998.pdf")
    index = build_pdf_index(tmp_path)

    res = resolve_source_pdf("Johnson", 2009, index)
    assert res.path is None
    assert res.reason == "no_match"


def test_tie_break_rules(tmp_path: Path):
    # Multiple candidates same key; ensure tie-break preferred
    touch(tmp_path / "Smith_2010_v2.pdf")
    touch(tmp_path / "Smith_2010_addendum.pdf")
    touch(tmp_path / "Smith_2010.pdf")
    touch(tmp_path / "Smith_2010_update_longername.pdf")
    index = build_pdf_index(tmp_path)

    res = resolve_source_pdf("Smith", 2010, index)
    assert res.path and res.path.name == "Smith_2010.pdf"
    assert res.reason == "ambiguous"  # multiple candidates


def test_secondary_override_choice(tmp_path: Path):
    # Simulate override: Amisi 2021 should pick Amisi_2021.pdf
    touch(tmp_path / "Amisi_2015.pdf")
    touch(tmp_path / "Amisi_2020.pdf")
    touch(tmp_path / "Amisi_2021.pdf")
    index = build_pdf_index(tmp_path)

    # If the row were secondary citing Amisi 2021, we should use those
    res = resolve_source_pdf("Amisi", 2021, index)
    assert res.path and res.path.name == "Amisi_2021.pdf"


def test_institutional_author_normalization(tmp_path: Path):
    # Institutional: use first alpha token normalized
    touch(tmp_path / "World_Bank_2023.pdf")
    index = build_pdf_index(tmp_path)

    # normalize 'World Bank' -> 'world' and match 2023
    assert normalize_lead_surname("World Bank") == "world"
    res = resolve_source_pdf("World Bank", 2023, index)
    assert res.path and res.path.name == "World_Bank_2023.pdf"


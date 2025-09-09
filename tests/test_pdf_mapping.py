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

    # normalize 'World Bank' -> 'world_bank' and match 2023
    assert normalize_lead_surname("World Bank") == "world_bank"
    res = resolve_source_pdf("World Bank", 2023, index)
    assert res.path and res.path.name == "World_Bank_2023.pdf"


def test_hyphenated_and_particles(tmp_path: Path):
    # Hyphenated surname and particles preserved (underscored)
    touch(tmp_path / "Cannon_Bowers_2023.pdf")
    touch(tmp_path / "de_Haan_2023.pdf")
    touch(tmp_path / "Van_den_Broeck_2021.pdf")
    touch(tmp_path / "van Wingerden_2017.pdf")
    touch(tmp_path / "CLEAR_AA_2020.pdf")
    touch(tmp_path / "Kirkhart_2000.pdf")
    touch(tmp_path / "Kuchenmuller_2022.pdf")
    touch(tmp_path / "Ripoll Lorenzo_2012.pdf")
    index = build_pdf_index(tmp_path)

    # Hyphenated: 'Cannon-Bowers' should match 'Cannon_Bowers'
    assert normalize_lead_surname("Cannon-Bowers") == "cannon_bowers"
    assert resolve_source_pdf("Cannon-Bowers", 2023, index).path.name == "Cannon_Bowers_2023.pdf"

    # Particles: 'de Haan'
    assert normalize_lead_surname("de Haan") == "de_haan"
    assert resolve_source_pdf("de Haan", 2023, index).path.name == "de_Haan_2023.pdf"

    # Multi-word with particles: 'Van den Broeck'
    assert normalize_lead_surname("Van den Broeck") == "van_den_broeck"
    assert resolve_source_pdf("Van den Broeck", 2021, index).path.name == "Van_den_Broeck_2021.pdf"

    # Particle fallback via citation_text: 'Wingerden' vs 'van Wingerden'
    r = resolve_source_pdf("Wingerden et al.", 2017, index, citation_text="(DeCorby-Watson et al., 2018; van Wingerden et al., 2017)")
    assert r.path and r.path.name == "van Wingerden_2017.pdf"

    # Corporate / hyphen-underscore normalization
    assert normalize_lead_surname("CLEAR-AA") == "clear_aa"
    assert resolve_source_pdf("CLEAR-AA", 2020, index).path.name == "CLEAR_AA_2020.pdf"

    # Possessive and diacritics
    assert normalize_lead_surname("Kirkhart’s") == "kirkhart"
    assert resolve_source_pdf("Kirkhart’s", 2000, index).path.name == "Kirkhart_2000.pdf"

    # Diacritics in surname
    assert normalize_lead_surname("Kuchenmüller") == "kuchenmuller"
    assert resolve_source_pdf("Kuchenmüller", 2022, index).path.name == "Kuchenmuller_2022.pdf"

    # Multi-word non-particle surname
    assert normalize_lead_surname("Ripoll Lorenzo") == "ripoll_lorenzo"
    assert resolve_source_pdf("Ripoll Lorenzo", 2012, index).path.name == "Ripoll Lorenzo_2012.pdf"

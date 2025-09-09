from audit_lib.enrich.section_scoring import best_section_for_claim


def test_best_section_penalizes_generic_headings() -> None:
    sections = [
        {"level": 2, "title": "Executive Summary", "body": "intro text"},
        {"level": 2, "title": "Methods", "body": "intro text"},
    ]
    title, canonical, level = best_section_for_claim("intro text", sections)
    assert canonical == "Methods"
    assert level == 2

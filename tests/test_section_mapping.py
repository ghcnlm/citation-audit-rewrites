from audit_lib.enrich import _best_section_for_claim


def test_best_section_for_claim_matches_relevant_section():
    sections = [
        {"title": "Introduction", "body": "Background information", "level": 2},
        {"title": "Results", "body": "The results show significant improvement", "level": 2},
    ]
    claim = "Our results show significant improvement."
    title, canonical, level = _best_section_for_claim(claim, sections)
    assert canonical == "Results"
    assert level == 2

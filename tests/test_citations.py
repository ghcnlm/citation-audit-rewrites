from audit_lib.citations import parse_citations


def test_parse_citations_identifies_types_and_authors():
    sentence = "As noted by Smith (2020), this is good (Brown, 2019)."
    results = parse_citations(sentence)
    assert any(r["author"] == "Smith" and r["citation_type"] == "narrative" for r in results)
    assert any(r["author"] == "Brown" and r["citation_type"] == "parenthetical" for r in results)
    assert len(results) == 2

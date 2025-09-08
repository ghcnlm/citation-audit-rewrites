import re
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z(“\"\[])')
def split_sentences(text: str):
    return [s.strip() for s in _SENT_SPLIT.split(text.strip()) if s.strip()]
def has_numbers(s: str) -> bool:
    return bool(re.search(r"\d", s))
def is_causal_or_normative(s: str) -> bool:
    return bool(re.search(r"\b(lead(?:s|ing)?\s+to|cause(?:s|d)?|result(?:s|ed)?\s+in|should|must|best\s+practice|therefore|hence)\b", s, re.I))

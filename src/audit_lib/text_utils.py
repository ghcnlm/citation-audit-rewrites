import re

_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z(“\"\[])')


def split_sentences(text: str) -> list[str]:
    """Split a block of text into individual sentences.

    Parameters
    ----------
    text: str
        Raw text to split.

    Returns
    -------
    list[str]
        List of sentences with surrounding whitespace removed. Returns an
        empty list when ``text`` is empty.
    """

    return [s.strip() for s in _SENT_SPLIT.split(text.strip()) if s.strip()]


def has_numbers(s: str) -> bool:
    """Check whether a string contains any numeric characters.

    Parameters
    ----------
    s: str
        String to inspect.

    Returns
    -------
    bool
        ``True`` if ``s`` contains at least one digit; otherwise ``False``.
    """

    return bool(re.search(r"\d", s))


def is_causal_or_normative(s: str) -> bool:
    """Determine if a string expresses causation or normative language.

    Parameters
    ----------
    s: str
        Sentence or phrase to inspect.

    Returns
    -------
    bool
        ``True`` if causal or normative keywords are found, otherwise
        ``False``.
    """

    return bool(
        re.search(
            r"\b(lead(?:s|ing)?\s+to|cause(?:s|d)?|result(?:s|ed)?\s+in|should|must|best\s+practice|therefore|hence)\b",
            s,
            re.I,
        )
    )

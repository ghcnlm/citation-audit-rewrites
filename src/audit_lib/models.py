from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class Citation:
    """Structured representation of a citation discovered in text."""
    citation_text: str
    citation_type: str
    author: str
    year: str
    is_secondary: bool
    primary_mentioned_author: Optional[str]
    primary_mentioned_year: Optional[str]
    stated_page: Optional[str]
    span: Tuple[int, int]

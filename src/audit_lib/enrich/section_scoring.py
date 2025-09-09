from __future__ import annotations
from typing import List, Dict, Tuple
import math
import re
import string

PUNCT_TABLE_SP = str.maketrans({c: " " for c in string.punctuation})
STOP = {
    "the","and","a","an","of","to","in","for","on","with","as","by","from","at","that","this","these","those",
    "is","are","was","were","be","been","being","it","its","their","there","which","or","not","but","if","than",
    "can","may","might","should","would","could","will","shall","do","does","did","done","such","into","over",
    "about","across","per","vs","via","within","between","among","both","also","more","most","much","many","some",
    "any","each","other","another","however","therefore","thus","so","because","while","where","when",
}

HEADING_PENALTY_PATTERNS = [
    r"\bexecutive\s+summary\b",
    r"\babstract\b",
    r"\boverview\b",
]


def tokens(text: str) -> List[str]:
    if not text:
        return []
    text = text.lower().translate(PUNCT_TABLE_SP)
    toks = [t for t in text.split() if len(t) > 1 and t not in STOP and t.isascii()]
    return toks


def tf(tokens: List[str]) -> Dict[str, float]:
    tf: Dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0.0) + 1.0
    n = float(len(tokens)) or 1.0
    for k in list(tf.keys()):
        tf[k] /= n
    return tf


def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = 0.0
    for k, v in a.items():
        if k in b:
            dot += v * b[k]
    na = math.sqrt(sum(v*v for v in a.values()))
    nb = math.sqrt(sum(v*v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def heading_penalty_factor(title: str) -> float:
    t = (title or "").lower()
    for pat in HEADING_PENALTY_PATTERNS:
        if re.search(pat, t):
            return 0.60
    return 1.0


def level_boost(level: int) -> float:
    return {4: 1.15, 3: 1.10, 2: 1.00, 1: 0.90}.get(level, 1.00)


def build_tfidf(section_bodies: List[List[str]]) -> Tuple[List[Dict[str, float]], Dict[str, float]]:
    tf_list = [tf(tokens) for tokens in section_bodies]
    df: Dict[str, int] = {}
    for tfd in tf_list:
        for term in tfd.keys():
            df[term] = df.get(term, 0) + 1
    N = float(len(tf_list)) or 1.0
    idf: Dict[str, float] = {}
    for term, cnt in df.items():
        idf[term] = math.log((N + 1.0) / (cnt + 1.0)) + 1.0
    return tf_list, idf


def apply_idf(tfd: Dict[str, float], idf: Dict[str, float]) -> Dict[str, float]:
    return {t: w * idf.get(t, 1.0) for t, w in tfd.items()}


def best_section_for_claim(claim_text: str, sections: List[Dict]) -> Tuple[str, str, int]:
    bodies_tokens = [tokens(s.get("body", "")) for s in sections]
    tf_list, idf = build_tfidf(bodies_tokens)
    claim_vec = apply_idf(tf(tokens(claim_text)), idf)
    best_score = -1.0
    best = ("unknown", "unknown", "")

    for s, tfd in zip(sections, tf_list):
        sec_vec = apply_idf(tfd, idf)
        sim = cosine(claim_vec, sec_vec)
        sim *= heading_penalty_factor(s.get("title", ""))
        sim *= level_boost(int(s.get("level", 2)))
        if sim > best_score:
            best_score = sim
            best = (
                s.get("title", "unknown"),
                s.get("title", "unknown"),
                int(s.get("level", 2)) if s.get("level") else "",
            )

    if best_score <= 0.0:
        claim_toks = set(tokens(claim_text))
        best2 = ("unknown", "unknown", "")
        best2_score = -1
        for s in sections:
            overlap = len(claim_toks.intersection(set(tokens(s.get("title", "")))))
            score = (
                overlap
                * heading_penalty_factor(s.get("title", ""))
                * level_boost(int(s.get("level", 2)))
            )
            if score > best2_score:
                best2_score = score
                best2 = (
                    s.get("title", "unknown"),
                    s.get("title", "unknown"),
                    int(s.get("level", 2)) if s.get("level") else "",
                )
        return best2

    return best

"""Regex patterns for "伤害中国人民的感情" and its variants.

All patterns run on text with whitespace removed (see normalize). Gaps may not
cross clause punctuation, so a match stays inside one clause.

Tier 1  the headline series: 伤害 … <the Chinese people> … 感情, active or passive.
        <the Chinese people> is 中国人民, 中华民族, 中国人, 我国人民, 中华儿女,
        炎黄子孙, 中国公众/百姓, 国人, or 中国 … 人民 (中国和亚洲各国人民,
        包括中国在内的…人民, 中国12亿人民, 中国各族人民).
Tier 2  伤害 … 感情 with a national/ethnic word in the match (两岸同胞, 海外华人,
        亚洲受害国人民, 民族感情 …). For hand review; not counted in tier 1.
Tier 3  any other 伤害 … 感情 (群众感情, 穆斯林感情 …). Kept for completeness.

Version 2 (2026-09-26): the nouns and gaps come from a hand review of all
tier 1 and tier 2 matches in 1946–2025 (data/review_labels.csv).
"""

import re
from dataclasses import dataclass

# Simplified and traditional forms.
HURT = "(?:伤|傷)害"
FEEL = "感情"
GAP = r"[^。！？；，、,;!?：:]"  # one character inside a clause
SUFFER = "(?:受|遭)"
ZH = "中(?:国|國)"
CN_PEOPLE = (
    "(?:"
    f"{ZH}人民|中(?:华|華)民族|{ZH}人|我(?:国|國)人民"
    "|中(?:华|華)(?:儿|兒)女|炎(?:黄|黃)子(?:孙|孫)"
    f"|{ZH}(?:公众|公眾|普通百姓|老百姓|百姓|民族)"
    "|中(?:韩|韓)(?:两|兩)(?:国|國)人民|(?:全世界|全球)(?:华|華)人"
    f"|{ZH}{GAP}{{0,16}}?(?:人民|国民|國民|(?:侨|僑)胞)"
    ")"
)

TIER1_ACTIVE = re.compile(rf"{HURT}{GAP}{{0,16}}?{CN_PEOPLE}{GAP}{{0,20}}?{FEEL}")
# 国人 alone is too broad (美国人, 受害国人民); accept it only right after 伤害.
TIER1_GUOREN = re.compile(rf"{HURT}(?:了|到)?(?:国|國)人(?:的)?{FEEL}")
TIER1_PASSIVE = re.compile(
    rf"{CN_PEOPLE}{GAP}{{0,8}}?{FEEL}{GAP}{{0,8}}?{SUFFER}{GAP}{{0,6}}?{HURT}"
)
BROAD_ACTIVE = re.compile(rf"{HURT}{GAP}{{0,20}}?{FEEL}")
BROAD_PASSIVE = re.compile(rf"{FEEL}{GAP}{{0,8}}?{SUFFER}{GAP}{{0,6}}?{HURT}")

NATIONAL = re.compile(
    "中(?:国|國)|中(?:华|華)|(?:华|華)人|(?:华|華)(?:侨|僑)|(?:侨|僑)胞|同胞|民族|(?:亿|億)|(?:国|國)人"
)
# "Do not (again) do things that hurt…", "avoid…", "we will not…", "any … that
# hurts" (a general warning). Looked for before the match, in the same clause;
# a list comma (、) does not end the clause here. 不能不 is a double negative;
# 绝不容忍 ("will never tolerate") goes with an accusation.
ADMONITION = re.compile(
    "不要|不再|不应|不應|不该|不該|不做|不能(?!不)|不会(?!容忍)|不會(?!容忍)|避免|防止|严防|嚴防"
    "|切勿|切不|别再|別再|(?:绝|絕|决|決)不(?!会容忍|會容忍|容忍)|无意|無意|任何"
)
BILATERAL = re.compile("(?:两|兩)(?:国|國)(?:人民|民族|国民|國民)|(?:双|雙)方人民")
_CLAUSE_END = re.compile(r"[。！？；，,;!?：:]")

PATTERNS = [
    (1, "active", TIER1_ACTIVE),
    (1, "active", TIER1_GUOREN),
    (1, "passive", TIER1_PASSIVE),
    (0, "active", BROAD_ACTIVE),   # tier 0 = decide 2 or 3 by NATIONAL
    (0, "passive", BROAD_PASSIVE),
]

_WS = re.compile(r"[\s　\xa0]+")


def normalize(text: str) -> str:
    return _WS.sub("", text)


@dataclass
class Hit:
    tier: int
    variant: str
    start: int
    end: int
    match: str
    admonition: bool
    bilateral: bool


def variant_of(match: str, form: str) -> str:
    if form == "passive":
        return "passive"
    if re.search("亿|億", match):
        return "N亿"
    if re.search("中(?:华|華)民族", match):
        return "中华民族"
    if "民族感情" in match:
        return "民族感情"
    if re.search(f"{ZH}人民", match):
        return "中国人民"
    if re.search(f"{ZH}{GAP}+(?:人民|国民|國民)", match):
        return "中国和…人民"
    if re.search(f"{ZH}人", match):
        return "中国人"
    return "other-noun"


def clause_before(text: str, start: int, width: int = 24) -> str:
    before = text[max(0, start - width):start]
    parts = _CLAUSE_END.split(before)
    return parts[-1]


def find_hits(text: str) -> list[Hit]:
    """Find all hits in normalized text. Tier 1 wins over broad matches on overlap."""
    if FEEL not in text:
        return []
    hits: list[Hit] = []
    for tier, form, pat in PATTERNS:
        for m in pat.finditer(text):
            if any(m.start() < h.end and h.start < m.end() for h in hits):
                continue
            s = m.group()
            t = tier or (2 if NATIONAL.search(s) else 3)
            hits.append(Hit(
                tier=t,
                variant=variant_of(s, form),
                start=m.start(),
                end=m.end(),
                match=s,
                admonition=bool(ADMONITION.search(clause_before(text, m.start()))),
                bilateral=bool(BILATERAL.search(s)),
            ))
    hits.sort(key=lambda h: h.start)
    return hits

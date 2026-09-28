import pytest

from feelings.patterns import find_hits, normalize


def tiers(text):
    return [(h.tier, h.variant) for h in find_hits(normalize(text))]


@pytest.mark.parametrize("text, variant", [
    # 1959-12-17, 陈嘉庚 on Indonesia; Wang's only pre-1978 article.
    ("甚至公然侮辱我国人民敬爱的领袖，严重地伤害了中国人民的感情。", "中国人民"),
    ("此人不仅拒绝为严重伤害中国人民感情的言行道歉", "中国人民"),
    ("极大地伤害了13亿中国人民的感情", "N亿"),
    ("严重伤害13亿中国人民感情", "N亿"),
    ("伤害了十三亿中国人民的感情", "N亿"),
    ("伤害中国人民的民族感情", "民族感情"),
    ("严重伤害了中华民族的感情", "中华民族"),
    ("伤害了包括台湾同胞在内的全体中国人民的感情", "中国人民"),
    ("伤害了中国人民和亚洲受害国人民的感情", "中国人民"),
    ("使中国人民的感情受到严重伤害", "passive"),
    ("嚴重傷害了中國人民的感情", "中国人民"),
    ("伤害 中国人民的\n感情", "中国人民"),
    # From the 2026-09-26 review: missed by version 1.
    ("严重伤害了中国和亚洲各国人民的感情", "中国和…人民"),
    ("伤害了包括中国在内的亚洲受害国人民的感情", "中国和…人民"),
    ("伤害了中国12亿人民的感情", "N亿"),
    ("严重地伤害了中国各族人民的感情", "中国和…人民"),
    ("伤害中国人民和其他遭受过侵略的亚洲国家人民的感情", "中国人民"),
    ("伤害了我国人民的感情", "other-noun"),
    ("伤害了海内外一切中华儿女的感情", "other-noun"),
    ("伤害了包括台湾同胞在内的全体炎黄子孙的感情", "other-noun"),
    ("深深地伤害了中国人的民族感情", "民族感情"),
    ("伤害了中国普通百姓的感情", "other-noun"),
    ("这则广告严重伤害了国人感情", "other-noun"),
    ("伤害了曾经被日本侵略过的中韩两国人民的感情", "other-noun"),
    ("伤害中国民族感情", "民族感情"),
    ("伤害了全世界华人的感情", "other-noun"),
])
def test_tier1(text, variant):
    assert tiers(text) == [(1, variant)]


@pytest.mark.parametrize("text", [
    "伤害了亚洲各受害国人民的感情",
    "伤害了美国人民的感情",
    "也严重伤害了两岸同胞的民族感情",
    "伤害了海外华人的感情",
    "伤害民族感情",
    "伤害了中日两国人民的感情",
])
def test_tier2(text):
    assert [t for t, _ in tiers(text)] == [2]


@pytest.mark.parametrize("text", [
    "伤害穆斯林宗教感情的行为",
    "严重伤害群众感情",
    "伤害的不仅是报考人员的感情",
])
def test_tier3(text):
    assert [t for t, _ in tiers(text)] == [3]


@pytest.mark.parametrize("text", [
    "中国人民的感情很深",
    "伤害了中国人民的利益。我们的感情",  # crosses a sentence end
    "伤害中国人民",
])
def test_no_match(text):
    assert tiers(text) == []


@pytest.mark.parametrize("text, flagged", [
    ("决不能伤害中国人民的感情", True),
    ("希望日方不要再做伤害中国人民感情的事", True),
    ("避免再次发生伤害中国人民感情的事情", True),
    ("不仅严重伤害了中国人民的感情", False),
    ("不惜伤害中国人民感情", False),
    ("这不能不严重伤害中国人民的感情", False),
    ("日本文部省不顾伤害中国人民的民族感情", False),
    ("绝不会容忍歪曲历史、伤害中国人民感情的挑衅", False),
    ("不要做干涉中国内政、伤害中国人民感情的事", True),
    ("任何伤害中国人民感情的行径", True),
])
def test_admonition_flag(text, flagged):
    (h,) = find_hits(normalize(text))
    assert h.admonition == flagged


def test_bilateral_flag():
    (h,) = find_hits(normalize("伤害了中日两国人民的感情"))
    assert h.bilateral
    (h,) = find_hits(normalize("严重破坏了两国关系，深深伤害了中国人民的感情"))
    assert not h.bilateral


def test_two_occurrences():
    text = "拒绝为严重伤害中国人民感情的言行道歉，否认历史真相、伤害中国人民感情"
    assert [t for t, _ in tiers(text)] == [1, 1]

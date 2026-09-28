"""Build data/counts_by_year.csv from hits.csv, corpus_size.csv and wang2014.csv.

Each year uses one source: Hugging Face where it has the year, else the e-paper.

Usage: uv run python -m feelings.aggregate
"""

import csv
from collections import defaultdict

from feelings.paths import DATA

FIELDS = [
    "year", "source", "tier1_articles", "tier1_articles_accusations", "tier1_occurrences",
    "tier1_per_10k_articles", "tier2_articles", "total_articles", "wang2014", "partial_year",
]


def read(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def is_accusation(hit) -> bool:
    """The hand review label decides. A match with no label (for example 2026) counts when it
    has no flag."""
    if hit["review_label"]:
        return hit["review_label"] == "yes"
    return hit["admonition"] == "0" and hit["bilateral"] == "0"


def main() -> None:
    sizes = {(r["source"], r["year"]): r for r in read("corpus_size.csv")}
    wang = {r["year"]: int(r["articles"]) for r in read("wang2014.csv")}
    years = sorted({y for _, y in sizes})
    source_of = {y: "hf" if ("hf", y) in sizes else "epaper" for y in years}

    t1_articles = defaultdict(set)
    t1_accusations = defaultdict(set)
    t1_occ = defaultdict(int)
    t2_articles = defaultdict(set)
    for h in read("hits.csv"):
        y = h["year"]
        if source_of.get(y) != h["source"]:
            continue
        if h["tier"] == "1":
            t1_articles[y].add(h["article_key"])
            t1_occ[y] += 1
            if is_accusation(h):
                t1_accusations[y].add(h["article_key"])
        elif h["tier"] == "2":
            t2_articles[y].add(h["article_key"])

    rows = []
    for y in years:
        size = sizes[(source_of[y], y)]
        total = int(size["articles"])
        n1 = len(t1_articles[y])
        rows.append({
            "year": y,
            "source": source_of[y],
            "tier1_articles": n1,
            "tier1_articles_accusations": len(t1_accusations[y]),
            "tier1_occurrences": t1_occ[y],
            "tier1_per_10k_articles": f"{n1 / total * 1e4:.2f}" if total else "",
            "tier2_articles": len(t2_articles[y] - t1_articles[y]),
            "total_articles": total,
            "wang2014": wang.get(y, 0) if 1949 <= int(y) <= 2013 else "",
            "partial_year": size["last_date"] if size["last_date"] < f"{y}-12-31" else "",
        })
    with (DATA / "counts_by_year.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} years")


if __name__ == "__main__":
    main()

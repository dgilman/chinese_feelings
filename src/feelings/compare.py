"""Comparison tables.

  wang     -> data/compare_wang.csv: Wang 2014 against this count, 1949–2013.
  overlap  -> data/overlap_check.csv: HF against e-paper, day by day, for the days
              crawled from both sources.

Usage: uv run python -m feelings.compare [wang|overlap]
"""

import csv
import gzip
import json
import sys
from collections import defaultdict

from feelings.paths import DATA, RAW_EPAPER, RAW_HF
from feelings.patterns import find_hits, normalize
from feelings.scan import iso_date


def read(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(name, fields, rows):
    with (DATA / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote data/{name} ({len(rows)} rows)")


def wang() -> None:
    ours = {r["year"]: r for r in read("counts_by_year.csv")}
    rows = []
    for r in read("wang2014.csv"):
        o = ours[r["year"]]
        w, t1, un = int(r["articles"]), int(o["tier1_articles"]), int(o["tier1_articles_accusations"])
        rows.append({
            "year": r["year"],
            "wang2014": w,
            "tier1_articles": t1,
            "tier1_articles_accusations": un,
            "tier2_articles": o["tier2_articles"],
            "diff_tier1": t1 - w,
            "diff_accusations": un - w,
            "total_articles": o["total_articles"],
        })
    totals = {k: sum(int(r[k]) for r in rows) for k in rows[0] if k != "year"}
    rows.append({"year": "total", **totals})
    write("compare_wang.csv", list(rows[0]), rows)


def load_days(path, days):
    """Return {date: [(title, normalized text)]} for the given days."""
    out = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            d = iso_date(rec.get("date"))
            if d in days:
                title = normalize((rec.get("title") or "").split("\n")[0])
                out[d].append((title, normalize(rec.get("text") or "")))
    return out


def overlap() -> None:
    ep_days = set()
    for p in RAW_EPAPER.glob("*.jsonl.gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            ep_days |= {iso_date(json.loads(line)["date"]) for line in f}
    hf_years = {p.name[:4] for p in RAW_HF.glob("*.jsonl.gz")}
    days = {d for d in ep_days if d[:4] in hf_years}
    hf, ep = defaultdict(list), defaultdict(list)
    for y in sorted({d[:4] for d in days}):
        hf.update(load_days(RAW_HF / f"{y}.jsonl.gz", days))
        ep.update(load_days(RAW_EPAPER / f"{y}.jsonl.gz", days))

    rows = []
    for d in sorted(days):
        h_texts = {t for _, t in hf[d]}
        e_texts = {t for _, t in ep[d]}
        h_titles = {t for t, _ in hf[d]}
        e_titles = {t for t, _ in ep[d]}
        rows.append({
            "date": d,
            "hf_articles": len(hf[d]),
            "epaper_articles": len(ep[d]),
            "hf_titles_in_epaper": len(h_titles & e_titles),
            "identical_texts": len(h_texts & e_texts),
            "hf_chars": sum(map(len, h_texts)),
            "epaper_chars": sum(map(len, e_texts)),
            "hf_tier1": sum(h.tier == 1 for t in h_texts for h in find_hits(t)),
            "epaper_tier1": sum(h.tier == 1 for t in e_texts for h in find_hits(t)),
        })
    write("overlap_check.csv", list(rows[0]) if rows else ["date"], rows)
    for r in rows:
        print(" ".join(f"{v}" for v in r.values()))


if __name__ == "__main__":
    {"wang": wang, "overlap": overlap}[sys.argv[1] if len(sys.argv) > 1 else "wang"]()

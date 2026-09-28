"""Scan all raw year files and write data/hits.csv and data/corpus_size.csv.

Usage: uv run python -m feelings.scan
"""

import csv
import gzip
import hashlib
import json
import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from feelings.paths import DATA, RAW_EPAPER, RAW_HF
from feelings.patterns import find_hits, normalize

CONTEXT = 60
HIT_FIELDS = [
    "hit_id", "date", "year", "source", "page", "title", "url", "tier", "variant",
    "admonition", "bilateral", "match", "context", "article_key", "review_label",
]
SIZE_FIELDS = ["source", "year", "articles", "characters", "days", "first_date", "last_date"]
_DATE = re.compile(r"(\d{4})\D(\d{1,2})\D(\d{1,2})")


def iso_date(raw: str) -> str:
    m = _DATE.match(raw or "")
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def scan_file(args: tuple[str, Path]) -> tuple[list[dict], list[dict]]:
    source, path = args
    hits, sizes = [], {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            date = iso_date(rec.get("date"))
            year = date[:4] or path.name[:4]
            title = (rec.get("title") or "").replace("\n", " ")
            text = normalize(rec.get("text") or "")
            s = sizes.setdefault(year, {"articles": 0, "characters": 0, "dates": set()})
            s["articles"] += 1
            s["characters"] += len(text)
            if date:
                s["dates"].add(date)
            found = find_hits(text)
            if not found:
                continue
            key = hashlib.sha1(f"{date}|{title}".encode()).hexdigest()[:12]
            for h in found:
                context = text[max(0, h.start - CONTEXT):h.end + CONTEXT]
                hits.append({
                    "hit_id": hashlib.sha1(f"{key}|{h.start}".encode()).hexdigest()[:12],
                    "date": date,
                    "year": year,
                    "source": source,
                    "page": rec.get("page") or "",
                    "title": title,
                    "url": rec.get("url") or "",
                    "tier": h.tier,
                    "variant": h.variant,
                    "admonition": int(h.admonition),
                    "bilateral": int(h.bilateral),
                    "match": h.match,
                    "context": context,
                    "article_key": key,
                    "review_label": "",
                })
    size_rows = [{
        "source": source,
        "year": year,
        "articles": s["articles"],
        "characters": s["characters"],
        "days": len(s["dates"]),
        "first_date": min(s["dates"], default=""),
        "last_date": max(s["dates"], default=""),
    } for year, s in sizes.items()]
    return hits, size_rows


def main() -> None:
    jobs = [("hf", p) for p in sorted(RAW_HF.glob("*.jsonl.gz"))]
    jobs += [("epaper", p) for p in sorted(RAW_EPAPER.glob("*.jsonl.gz"))]
    all_hits, all_sizes = [], []
    with ProcessPoolExecutor() as pool:
        for (source, path), (hits, sizes) in zip(jobs, pool.map(scan_file, jobs)):
            n1 = sum(h["tier"] == 1 for h in hits)
            print(f"{source} {path.name}: {n1} tier-1 hits, {len(hits)} total", flush=True)
            all_hits += hits
            all_sizes += sizes
    all_hits.sort(key=lambda h: (h["source"], h["date"], h["article_key"]))
    labels = DATA / "review_labels.csv"
    if labels.exists():
        with labels.open(encoding="utf-8") as f:
            by_id = {r["hit_id"]: r["label"] for r in csv.DictReader(f)}
        for h in all_hits:
            h["review_label"] = by_id.get(h["hit_id"], "")
    all_sizes.sort(key=lambda s: (s["source"], s["year"]))
    for name, fields, rows in [
        ("hits.csv", HIT_FIELDS, all_hits),
        ("corpus_size.csv", SIZE_FIELDS, all_sizes),
    ]:
        with (DATA / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    print(f"wrote {len(all_hits)} hits, {len(all_sizes)} corpus rows")


if __name__ == "__main__":
    main()

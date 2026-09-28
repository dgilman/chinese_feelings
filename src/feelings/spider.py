"""Spider the People's Daily e-paper (paper.people.com.cn, issues from 2024-12-01 on).

Every fetched page is kept gzipped under data/raw/epaper_html/, so a re-run or a
re-parse needs no network. Parsed articles go to data/raw/epaper/YYYY.jsonl.gz in
the same schema as the Hugging Face files (date, page, title, text, url).

Usage: uv run python -m feelings.spider 2026-01-01 [2026-09-26]
       uv run python -m feelings.spider --dates 2025-03-02 2025-07-19 ...
"""

import datetime as dt
import gzip
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request

from feelings.paths import RAW_EPAPER, RAW_EPAPER_HTML

BASE = "http://paper.people.com.cn/rmrb/pc"
DELAY = 2.0
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) research-crawler"
DONE_FILE = RAW_EPAPER / "done_days.txt"
# Retry for about 4 hours before giving up, so that a network outage or sleep does
# not stop a long crawl.
MAX_ATTEMPTS = 30
MAX_BACKOFF = 600

_last_request = 0.0


def fetch(url: str, cache_path) -> str | None:
    """Return the page text, from cache if present. None on 404."""
    global _last_request
    if cache_path.exists():
        return gzip.decompress(cache_path.read_bytes()).decode("utf-8")
    for attempt in range(MAX_ATTEMPTS):
        wait = DELAY - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except OSError as e:  # URLError, timeouts, "Network is down"
            err = e
        else:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = cache_path.with_suffix(".tmp")
            tmp.write_bytes(gzip.compress(body.encode("utf-8")))
            tmp.rename(cache_path)
            return body
        backoff = min(DELAY * 2 ** (attempt + 1), MAX_BACKOFF)
        print(f"  retry {attempt + 1} for {url}: {err}; sleep {backoff:.0f}s", file=sys.stderr)
        time.sleep(backoff)
    raise RuntimeError(f"giving up on {url}")


def _clean(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", "", fragment)
    return html.unescape(text).replace("\xa0", " ").strip()


def parse_node(body: str) -> tuple[str, list[str], list[str]]:
    """Return (page name, node file names, article ids) for one page index."""
    m = re.search(r'<div class="paper-bot">.*?(第\d+版：[^<\s]*)', body, re.S)
    page = m.group(1) if m else ""
    nodes = sorted(set(re.findall(r'href="(node_\d+\.html)"', body)))
    articles = list(dict.fromkeys(re.findall(r"content_(\d+)\.html", body)))
    return page, nodes, articles


def parse_article(body: str) -> dict:
    content = re.search(r"<!--enpcontent-->(.*?)<!--/enpcontent-->", body, re.S)
    paras = re.findall(r"<p[^>]*>(.*?)</p>", content.group(1), re.S) if content else []
    text = "\n".join(p for p in (_clean(x) for x in paras) if p)
    prop = re.search(r"<!--enpproperty(.*?)/enpproperty-->", body, re.S)
    prop = prop.group(1) if prop else ""

    def field(name):
        m = re.search(rf"<{name}>(.*?)</{name}>", prop, re.S)
        return _clean(m.group(1)) if m else ""

    title = field("title")
    subtitle = field("subtitle")
    return {
        "introtitle": field("introtitle"),
        "title": title + ("\n" + subtitle if subtitle else ""),
        "text": text,
    }


def crawl_day(day: dt.date) -> list[dict] | None:
    ym, d = day.strftime("%Y%m"), day.strftime("%d")
    cache = RAW_EPAPER_HTML / ym / d
    first = fetch(f"{BASE}/layout/{ym}/{d}/node_01.html", cache / "node_01.html.gz")
    if first is None:
        return None
    _, nodes, _ = parse_node(first)
    records = []
    for node in nodes:
        body = fetch(f"{BASE}/layout/{ym}/{d}/{node}", cache / f"{node}.gz")
        if body is None:
            continue
        page, _, article_ids = parse_node(body)
        for aid in article_ids:
            url = f"{BASE}/content/{ym}/{d}/content_{aid}.html"
            art = fetch(url, cache / f"content_{aid}.html.gz")
            if art is None:
                continue
            rec = parse_article(art)
            records.append({
                "date": day.strftime("%Y.%m.%d"),
                "page": page,
                "title": rec["title"],
                "introtitle": rec["introtitle"],
                "text": rec["text"],
                "url": url,
            })
    return records


def date_range(start: dt.date, end: dt.date) -> list[dt.date]:
    return [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]


def main(argv: list[str]) -> None:
    if argv[1] == "--dates":
        days = sorted(dt.date.fromisoformat(a) for a in argv[2:])
    else:
        start = dt.date.fromisoformat(argv[1])
        end = dt.date.fromisoformat(argv[2]) if len(argv) > 2 else dt.date.today()
        days = date_range(start, end)
    RAW_EPAPER.mkdir(parents=True, exist_ok=True)
    done = set(DONE_FILE.read_text().split()) if DONE_FILE.exists() else set()
    for day in days:
        key = day.isoformat()
        if key not in done:
            t0 = time.monotonic()
            records = crawl_day(day)
            if records:
                # Multi-member gzip: appending a new member per day is valid.
                with gzip.open(RAW_EPAPER / f"{day.year}.jsonl.gz", "at", encoding="utf-8") as f:
                    for r in records:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
            with DONE_FILE.open("a") as f:
                f.write(key + "\n")
            n = "no issue" if records is None else f"{len(records)} articles"
            print(f"{key}: {n} ({time.monotonic() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main(sys.argv)

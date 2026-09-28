"""Download the People's Daily corpus (1946–2025) from Hugging Face.

Dataset: Papersnake/people_daily_news (CC0). Files already present with the
right size are skipped.

Usage: uv run python -m feelings.fetch_hf
"""

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from feelings.paths import RAW_HF

REPO = "Papersnake/people_daily_news"
API = f"https://huggingface.co/api/datasets/{REPO}/tree/main"
FILE_URL = f"https://huggingface.co/datasets/{REPO}/resolve/main/{{}}"


def list_files() -> list[tuple[str, int]]:
    with urllib.request.urlopen(API, timeout=60) as resp:
        tree = json.load(resp)
    return [(e["path"], e["size"]) for e in tree if e["path"].endswith(".jsonl.gz")]


def download(name: str, size: int) -> str:
    dest = RAW_HF / name
    if dest.exists() and dest.stat().st_size == size:
        return f"{name}: present"
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(FILE_URL.format(name), timeout=120) as resp, tmp.open("wb") as f:
        while chunk := resp.read(1 << 20):
            f.write(chunk)
    if tmp.stat().st_size != size:
        raise RuntimeError(f"{name}: got {tmp.stat().st_size} bytes, expected {size}")
    tmp.rename(dest)
    return f"{name}: {size / 1e6:.1f} MB"


def main() -> None:
    RAW_HF.mkdir(parents=True, exist_ok=True)
    files = list_files()
    (RAW_HF / "manifest.json").write_text(json.dumps(dict(files), indent=1))
    with ThreadPoolExecutor(4) as pool:
        for msg in pool.map(lambda f: download(*f), files):
            print(msg, flush=True)


if __name__ == "__main__":
    main()

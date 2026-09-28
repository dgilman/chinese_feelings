from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
RAW_HF = RAW / "hf"
RAW_EPAPER = RAW / "epaper"            # parsed articles, YYYY.jsonl.gz
RAW_EPAPER_HTML = RAW / "epaper_html"  # every fetched page, gzipped

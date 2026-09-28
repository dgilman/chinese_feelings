"""Write the Commons Data: pages for the Chart extension.

Output: data/wiki/<TAB_NAME> and data/wiki/<CHART_NAME>, JSON ready to paste into
https://commons.wikimedia.org/wiki/Data:<name>. See HANDOFF.md.

Usage: uv run python -m feelings.wiki_export
"""

import csv
import json

from feelings.paths import DATA

TAB_NAME = "People's Daily hurt the feelings of the Chinese people.tab"
CHART_NAME = "People's Daily hurt the feelings of the Chinese people.Line.chart"
REPO_URL = "<repository URL>"


def main() -> None:
    with (DATA / "counts_by_year.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    partial = next((r["partial_year"] for r in rows if r["partial_year"]), "")

    tab = {
        "license": "CC0-1.0",
        "description": {
            "en": "Articles per year in the People's Daily that contain "
                  "'hurt the feelings of the Chinese people' (伤害…中国人民/中华民族…感情)",
            "zh-hans": "《人民日报》每年出现“伤害中国人民（中华民族）感情”的文章数",
            "zh-hant": "《人民日報》每年出現「傷害中國人民（中華民族）感情」的文章數",
        },
        "sources": (
            "People's Daily full text 1946–2025: Hugging Face Papersnake/people_daily_news (CC0); "
            "2026: paper.people.com.cn. Regex count, method and code: " + REPO_URL + ". "
            "Comparison series: 汪宏倫 (Wang Horng-luen), 理解當代中國民族主義, 文化研究 19 (2014): 189–250, fig. 1."
        ),
        "schema": {"fields": [
            {"name": "year", "type": "string", "title": {"en": "Year", "zh": "年份"}},
            {"name": "articles", "type": "number",
             "title": {"en": "Articles (this count)", "zh-hans": "文章数（本统计）", "zh-hant": "文章數（本統計）"}},
            {"name": "wang2014", "type": "number",
             "title": {"en": "Articles (Wang 2014)", "zh-hans": "文章数（汪宏伦 2014）", "zh-hant": "文章數（汪宏倫 2014）"}},
        ]},
        "data": [
            [r["year"], int(r["tier1_articles"]), int(r["wang2014"]) if r["wang2014"] else None]
            for r in rows
        ],
    }

    subtitle = {
        "en": f"{rows[0]['year']}–{rows[-1]['year']}",
        "zh-hans": f"{rows[0]['year']}–{rows[-1]['year']}年",
        "zh-hant": f"{rows[0]['year']}–{rows[-1]['year']}年",
    }
    if partial:
        subtitle["en"] += f"; {partial[:4]} to {partial} only"
        subtitle["zh-hans"] += f"；{partial[:4]}年截至{partial}"
        subtitle["zh-hant"] += f"；{partial[:4]}年截至{partial}"

    chart = {
        "license": "CC0-1.0",
        "version": 1,
        "type": "line",
        "source": TAB_NAME,
        "title": {
            "en": "\"Hurt the feelings of the Chinese people\" in the People's Daily",
            "zh-hans": "《人民日报》“伤害中国人民的感情”出现次数",
            "zh-hant": "《人民日報》「傷害中國人民的感情」出現次數",
        },
        "subtitle": subtitle,
        "xAxis": {"title": {"en": "Year", "zh": "年份"}},
        "yAxis": {"title": {"en": "Articles", "zh-hans": "文章数", "zh-hant": "文章數"}},
    }

    out = DATA / "wiki"
    out.mkdir(exist_ok=True)
    for name, obj in [(TAB_NAME, tab), (CHART_NAME, chart)]:
        (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"wrote data/wiki/{name}")


if __name__ == "__main__":
    main()

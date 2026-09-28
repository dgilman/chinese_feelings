"""Draw the graph for the blog: articles per year, with Wang 2014 as a second line.

Output: data/blog/feelings_by_year.svg and, if rsvg-convert is installed, a PNG at 2x.

Usage: uv run python -m feelings.blog_chart
"""

import csv
import datetime
import shutil
import subprocess
from xml.sax.saxutils import escape

from feelings.paths import DATA

W, H = 960, 540
LEFT, RIGHT, TOP, BOTTOM = 56, 24, 132, 84
Y_MAX, Y_STEP = 50, 10
MIN_RUN = 6  # empty years in a row that become an axis break
BREAK_W = 5  # width of a break, in columns

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BLUE = "#2a78d6"
BLUE_LIGHT = "#9ec5f4"
ORANGE = "#eb6834"
FONT = "-apple-system, 'Helvetica Neue', Arial, sans-serif"


def text(x, y, s, size=13, fill=INK_2, anchor="start", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{escape(s)}</text>')


def column(x, y, w, h, fill):
    """A column with rounded top corners and a square base."""
    r = min(3, w / 2, h)
    return (f'<path d="M{x:.2f},{y + h:.2f} V{y + r:.2f} Q{x:.2f},{y:.2f} {x + r:.2f},{y:.2f} '
            f'H{x + w - r:.2f} Q{x + w:.2f},{y:.2f} {x + w:.2f},{y + r:.2f} V{y + h:.2f} Z" fill="{fill}"/>')


def empty(r) -> bool:
    return r["tier1_articles"] == "0" and r["wang2014"] in ("", "0") and not r["partial_year"]


def layout(rows):
    """Slots along the x axis: ("year", row) or ("break", first year, last year).

    A run of MIN_RUN or more empty years becomes one break, but the empty years next to a year
    with articles stay, so that the line of the other series keeps its shape.
    """
    slots, i = [], 0
    while i < len(rows):
        j = i
        while j < len(rows) and empty(rows[j]):
            j += 1
        a, b = i + (i > 0), j - 1 - (j < len(rows))  # keep one empty year next to a non-empty year
        if b - a + 1 >= MIN_RUN:
            slots += [("year", r) for r in rows[i:a]]
            slots.append(("break", rows[a]["year"], rows[b]["year"]))
            slots += [("year", r) for r in rows[b + 1:j]]
        else:
            slots += [("year", r) for r in rows[i:j]]
        if j < len(rows):
            slots.append(("year", rows[j]))
        i = j + 1
    return slots


def main() -> None:
    with (DATA / "counts_by_year.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    first, last = rows[0]["year"], rows[-1]["year"]
    partial = next((r["partial_year"] for r in rows if r["partial_year"]), "")
    partial_label = ""
    if partial:
        d = datetime.date.fromisoformat(partial)
        partial_label = f"{d.day} {d:%B} {d.year}"

    slots = layout(rows)
    pw, ph = W - LEFT - RIGHT, H - TOP - BOTTOM
    band = pw / sum(BREAK_W if s[0] == "break" else 1 for s in slots)
    bar_w = band - 2  # 2px surface gap between columns
    y_of = lambda v: TOP + ph - v / Y_MAX * ph
    x_of = {}  # year -> left edge of its column
    segments = [[]]  # runs of years with no break between them
    breaks = []  # (left x, right x, first year, last year)
    x = LEFT
    for s in slots:
        if s[0] == "break":
            breaks.append((x, x + BREAK_W * band, s[1], s[2]))
            segments.append([])
            x += BREAK_W * band
        else:
            x_of[s[1]["year"]] = x
            segments[-1].append(s[1])
            x += band
    segments = [seg for seg in segments if seg]

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="{FONT}">',
           '<defs><pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse" '
           f'patternTransform="rotate(45)"><rect width="4" height="4" fill="{BLUE_LIGHT}"/>'
           f'<line x1="0" y1="0" x2="0" y2="4" stroke="{BLUE}" stroke-width="1.5"/></pattern></defs>',
           f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>']

    # Title and subtitle
    out.append(text(LEFT, 34, "“Hurt the feelings of the Chinese people” in the People’s Daily",
                     size=20, fill=INK, weight="bold"))
    sub = f"Number of articles per year that contain the phrase, {first} to {partial_label or last}"
    out.append(text(LEFT, 58, sub, size=14))

    # Legend
    lx, ly = LEFT, 90
    out.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" rx="2" fill="{BLUE}"/>')
    out.append(text(lx + 18, ly, "Usage"))
    lx += 90
    out.append(f'<line x1="{lx}" y1="{ly - 4}" x2="{lx + 18}" y2="{ly - 4}" stroke="{ORANGE}" '
               'stroke-width="2" stroke-linecap="round"/>')
    out.append(text(lx + 24, ly, "Wang (2014), 1949–2013"))
    if partial:
        lx += 200
        out.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" rx="2" fill="url(#hatch)"/>')
        out.append(text(lx + 18, ly, "Partial year"))

    # Grid and y axis, interrupted at each break
    spans = [(x_of[seg[0]["year"]], x_of[seg[-1]["year"]] + band) for seg in segments]
    for v in range(0, Y_MAX + 1, Y_STEP):
        y = y_of(v)
        color = BASELINE if v == 0 else GRID
        for x0, x1 in spans:
            out.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" stroke="{color}" stroke-width="1"/>')
        out.append(text(LEFT - 8, y + 4, str(v), size=12, fill=MUTED, anchor="end"))
    out.append(text(LEFT - 8, TOP - 14, "Articles", size=12, fill=MUTED, anchor="end"))

    # Breaks: a break mark on the baseline, the years below, "none" above
    y0 = y_of(0)
    for bx0, bx1, a, b in breaks:
        cx = (bx0 + bx1) / 2
        for dx in (-3, 3):
            out.append(f'<line x1="{cx + dx - 3:.1f}" y1="{y0 + 5:.1f}" x2="{cx + dx + 3:.1f}" y2="{y0 - 5:.1f}" '
                       f'stroke="{MUTED}" stroke-width="1.5" stroke-linecap="round"/>')
        out.append(text(cx, y0 - 12, "none", size=11, fill=MUTED, anchor="middle"))
        out.append(text(cx, y0 + 20, f"{a}–{b[2:]}", size=12, fill=MUTED, anchor="middle"))

    # X axis labels: each decade and the last year; in a short segment between breaks, the years with articles
    for seg in segments:
        short = len(seg) < 5
        for r in seg:
            if (int(r["tier1_articles"]) > 0) if short else int(r["year"]) % 10 == 0 or r is rows[-1]:
                out.append(text(x_of[r["year"]] + band / 2, y0 + 20, r["year"], size=12, fill=MUTED, anchor="middle"))

    # Columns
    for r in rows:
        v = int(r["tier1_articles"])
        if v == 0:
            continue
        fill = "url(#hatch)" if r["partial_year"] else BLUE
        out.append(column(x_of[r["year"]] + 1, y_of(v), bar_w, y0 - y_of(v), fill))

    # Wang 2014 line, one piece per segment
    for seg in segments:
        pts = [(x_of[r["year"]] + band / 2, y_of(int(r["wang2014"]))) for r in seg if r["wang2014"]]
        if len(pts) > 1:
            out.append('<polyline fill="none" stroke="{}" stroke-width="2" stroke-linejoin="round" '
                       'stroke-linecap="round" points="{}"/>'.format(
                           ORANGE, " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)))

    # Direct labels: the two highest years
    for r in sorted(rows, key=lambda r: -int(r["tier1_articles"]))[:2]:
        v, year = int(r["tier1_articles"]), r["year"]
        out.append(text(x_of[year] + band / 2, y_of(v) - 6, f"{year}: {v}", size=12, fill=INK, anchor="middle"))

    # Source
    src = [f"Source: People’s Daily full text, {first}–{int(last) - 1} from the Hugging Face data set "
           f"Papersnake/people_daily_news, {last} from paper.people.com.cn.",
           "An article counts one time if it contains the phrase one or more times. "
           "Second line: Wang Horng-luen (2014), fig. 1."]
    for i, s in enumerate(src):
        out.append(text(LEFT, H - 34 + i * 16, s, size=11, fill=MUTED))

    out.append("</svg>")

    dest = DATA / "blog"
    dest.mkdir(exist_ok=True)
    svg = dest / "feelings_by_year.svg"
    svg.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {svg.relative_to(DATA.parent)}")
    if shutil.which("rsvg-convert"):
        png = svg.with_suffix(".png")
        subprocess.run(["rsvg-convert", "-z", "2", "-o", str(png), str(svg)], check=True)
        print(f"wrote {png.relative_to(DATA.parent)}")


if __name__ == "__main__":
    main()

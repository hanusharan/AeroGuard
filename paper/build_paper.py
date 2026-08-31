"""Render paper/AeroGuard_Research_Paper.md to a two-column academic PDF.

The Markdown file is the single source of truth. This script converts it to a
print-styled HTML document and then to PDF with headless Chrome (no LaTeX
toolchain is installed on this machine, so the typesetting is done in CSS).

Run:  .venv/bin/python paper/build_paper.py
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "AeroGuard_Research_Paper.md"
HTML_OUT = HERE / "AeroGuard_Research_Paper.html"
PDF_OUT = HERE / "AeroGuard_Research_Paper.pdf"

# The dashboard serves the paper as a static asset. Publishing into Vite's
# `public/` keeps `npm run dev` and `npm run build` in sync automatically, so
# the site's paper links work locally and on GitHub Pages without a bespoke
# copy step. `paper/` remains the source of truth; this is the published copy.
PUBLISH_DIR = HERE.parent / "dashboard" / "public" / "paper"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
]

CSS = """
@page { size: letter; margin: 0.54in 0.55in 0.46in 0.55in; }
@page { @bottom-center { content: counter(page); } }

:root {
  --ink: #101418;
  --ink-soft: #3d454e;
  --rule: #c8cdd4;
  --accent: #7a2020;
  --serif: "Charter", "Palatino Linotype", "Palatino", "Georgia", "Times New Roman", serif;
  --sans: "Helvetica Neue", "Helvetica", "Arial", sans-serif;
  --mono: "SFMono-Regular", "Menlo", "Consolas", monospace;
}

html { font-size: 8.2pt; }
body {
  font-family: var(--serif);
  color: var(--ink);
  line-height: 1.235;
  text-align: justify;
  hyphens: auto;
  -webkit-hyphens: auto;
  margin: 0;
}

/* ---------- masthead (spans both columns) ---------- */
.masthead { text-align: center; margin: 0 0 9pt; }
h1.title {
  font-family: var(--sans);
  font-size: 16.4pt;
  line-height: 1.15;
  font-weight: 700;
  letter-spacing: -0.005em;
  margin: 0 0 7pt;
  text-align: center;
  hyphens: none;
}
.authors { font-family: var(--sans); font-size: 9.2pt; line-height: 1.45; color: var(--ink-soft); }
.authors .name { font-size: 10.5pt; color: var(--ink); font-weight: 600; }
.authors code { font-family: var(--mono); font-size: 8.2pt; }

.abstract {
  margin: 9pt auto 0;
  padding: 6.5pt 9pt;
  border-top: 1.1pt solid var(--ink);
  border-bottom: 0.5pt solid var(--rule);
  font-size: 8.25pt;
  line-height: 1.26;
  text-align: justify;
}
.abstract p { margin: 0 0 5pt; }
.abstract p:last-child { margin-bottom: 0; }
.abstract .idx { font-size: 8.4pt; }

/* ---------- two-column body ---------- */
.body {
  column-count: 2;
  column-gap: 0.26in;
  column-fill: balance;
  margin-top: 9pt;
}

h2 {
  font-family: var(--sans);
  font-size: 9.9pt;
  font-weight: 700;
  margin: 7pt 0 2.5pt;
  text-align: left;
  hyphens: none;
  break-after: avoid;
}
h3 {
  font-family: var(--sans);
  font-size: 9.0pt;
  font-weight: 600;
  font-style: italic;
  margin: 7pt 0 2.5pt;
  text-align: left;
  hyphens: none;
  break-after: avoid;
}
h2:first-child, h3:first-child { margin-top: 0; }

p { margin: 0 0 4.8pt; orphans: 2; widows: 2; }
p + p { text-indent: 0; }
strong { font-weight: 700; }
code { font-family: var(--mono); font-size: 0.87em; background: #f2f3f5; padding: 0 1.5px; border-radius: 2px; }
.nw { white-space: nowrap; }
sub, sup { line-height: 0; font-size: 0.72em; }

/* ---------- equations ---------- */
.eq {
  margin: 5pt 0 6pt;
  font-family: var(--serif);
  font-size: 9.1pt;
  break-inside: avoid;
}
.eq .line { display: flex; align-items: baseline; margin: 2pt 0; }
.eq .expr { flex: 1; text-align: center; }
.eq .num { width: 2.2em; text-align: right; font-style: normal; font-size: 8.6pt; }

/* ---------- figures ---------- */
figure {
  margin: 7pt 0 8pt;
  break-inside: avoid;
  text-align: center;
}
figure img { max-width: 100%; height: auto; }
figcaption {
  font-family: var(--sans);
  font-size: 7.3pt;
  line-height: 1.28;
  color: var(--ink-soft);
  text-align: justify;
  margin-top: 3pt;
}
figure.span, .tablewrap.span {
  column-span: all;
  margin: 8pt 0 9pt;
}

/* ---------- tables ---------- */
.tablewrap { break-inside: avoid; margin: 9pt 0 10pt; }
.tablewrap .caption {
  font-family: var(--sans);
  font-size: 7.3pt;
  line-height: 1.28;
  color: var(--ink-soft);
  text-align: justify;
  margin-bottom: 3pt;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--sans);
  font-size: 6.9pt;
  table-layout: fixed;
}
th, td {
  padding: 2.2pt 2.2pt;
  text-align: right;
  vertical-align: top;
  hyphens: none;
}
th:first-child, td:first-child { text-align: left; width: 30%; }
td, th { overflow-wrap: anywhere; }
thead th { border-top: 1.1pt solid var(--ink); border-bottom: 0.6pt solid var(--ink); font-weight: 600; }
tbody tr:last-child td { border-bottom: 1.1pt solid var(--ink); }
tbody tr + tr td { border-top: 0.35pt solid #e2e5e9; }

/* ---------- references ---------- */
.refs {
  font-size: 6.95pt;
  line-height: 1.22;
  text-align: left;
  hyphens: none;
  column-span: all;
  column-count: 3;
  column-gap: 0.2in;
}
.refs .ref {
  padding-left: 1.85em;
  text-indent: -1.85em;
  margin: 0 0 2.4pt;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.refs code { font-size: 0.9em; background: none; padding: 0; overflow-wrap: anywhere; }

.sources {
  column-span: all;
  margin-top: 5pt;
  font-size: 6.95pt;
  line-height: 1.235;
  text-align: justify;
  hyphens: none;
  overflow-wrap: anywhere;
}
.sources code { font-size: 0.93em; background: none; padding: 0; }
.sources .disclaimer { display: block; margin-top: 4pt; padding-top: 3.5pt; border-top: 0.5pt solid var(--rule); text-align: center; }

/* ---------- on-screen reading view ----------
   The two-column measure is right for print but hostile on screen (scroll
   down one column, back up for the next). For screen the document collapses
   to a single readable column on a paper-like sheet; print keeps the
   two-column layout above verbatim. */
@media screen {
  html { font-size: 11.5pt; background: #eceff3; }
  body {
    max-width: 46em;
    margin: 0 auto;
    padding: 3.2em 2.2em 4em;
    background: #fff;
    line-height: 1.5;
  }
  .body { column-count: 1; }
  h1.title { font-size: 2.05em; }
  .abstract { font-size: 0.94em; line-height: 1.5; }
  .refs { column-count: 2; font-size: 0.8em; line-height: 1.45; }
  .sources { font-size: 0.78em; line-height: 1.5; }
  figure.fig, .tablewrap { margin: 1.6em 0; }
  figure img { max-width: min(100%, 34em); }
  figcaption, .tablewrap .caption { font-size: 0.8em; line-height: 1.45; }
  table { font-size: 0.82em; }
  .eq { font-size: 1em; }
}
@media screen and (max-width: 640px) {
  html { font-size: 11pt; }
  body { padding: 2em 1.1em 3em; }
  .refs { column-count: 1; }
  .tablewrap { overflow-x: auto; }
}

.footer {
  column-span: all;
  margin-top: 6pt;
  padding-top: 4pt;
  border-top: 0.5pt solid var(--rule);
  font-family: var(--sans);
  font-size: 7.6pt;
  line-height: 1.35;
  color: var(--ink-soft);
  text-align: center;
}
"""


# --------------------------------------------------------------- inline
def inline(text: str) -> str:
    """Markdown inline -> HTML. Raw HTML in the source is passed through."""
    out = re.sub(r"`([^`]+)`", lambda m: f"<code>{html.escape(m.group(1))}</code>", text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", out)
    out = out.replace("\\*", "*")
    return out


def table_html(lines: list[str]) -> str:
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
    head, body = rows[0], rows[2:]
    th = "".join(f"<th>{inline(c)}</th>" for c in head)
    tb = "".join(
        "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body
    )
    return f"<table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table>"


# --------------------------------------------------------------- parser
def convert(md: str) -> str:
    lines = md.split("\n")
    title = ""
    masthead: list[str] = []
    body: list[str] = []
    target = body
    i = 0
    while i < len(lines):
        ln = lines[i]

        if ln.startswith("# "):
            title = inline(ln[2:].strip())
            i += 1
            continue

        # ---- fenced blocks
        m = re.match(r"^:::(\w+)(.*)$", ln)
        if m:
            kind, attr_s = m.group(1), m.group(2)
            attrs = dict(re.findall(r"(\w+)=([^\s]+)", attr_s))
            block: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                block.append(lines[i])
                i += 1
            i += 1
            target = body

            if kind == "authors":
                parts = [p for p in block if p.strip()]
                inner = f'<div class="name">{inline(parts[0])}</div>'
                inner += "".join(f"<div>{inline(p)}</div>" for p in parts[1:])
                masthead.append(f'<div class="authors">{inner}</div>')

            elif kind == "abstract":
                paras = "\n".join(block).split("\n\n")
                inner = ""
                for p in paras:
                    if not p.strip():
                        continue
                    cls = ' class="idx"' if p.strip().startswith("**Index terms**") else ""
                    inner += f"<p{cls}>{inline(p.strip())}</p>"
                masthead.append(f'<div class="abstract">{inner}</div>')

            elif kind == "eq":
                inner = ""
                for raw in block:
                    if not raw.strip():
                        continue
                    mm = re.match(r"^(.*?)\s*\((\d+)\)\s*$", raw.strip())
                    expr, num = (mm.group(1), mm.group(2)) if mm else (raw.strip(), "")
                    inner += (
                        f'<div class="line"><span class="expr">{inline(expr)}</span>'
                        f'<span class="num">{f"({num})" if num else ""}</span></div>'
                    )
                body.append(f'<div class="eq">{inner}</div>')

            elif kind == "figure":
                span = " span" if attrs.get("span") == "true" else ""
                width = attrs.get("width")
                style = f' style="width:{width}"' if width else ""
                cap = inline(" ".join(x.strip() for x in block if x.strip()))
                body.append(
                    f'<figure class="fig{span}" id="{attrs.get("id","")}">'
                    f'<img src="{attrs.get("src","")}"{style} alt="">'
                    f"<figcaption>{cap}</figcaption></figure>"
                )

            elif kind == "table":
                cap_lines = [x for x in block if not x.strip().startswith("|") and x.strip()]
                tbl_lines = [x for x in block if x.strip().startswith("|")]
                body.append(
                    f'<div class="tablewrap" id="{attrs.get("id","")}">'
                    f'<div class="caption">{inline(" ".join(cap_lines))}</div>'
                    f"{table_html(tbl_lines)}</div>"
                )

            elif kind == "refs":
                inner = "".join(
                    f'<div class="ref">{inline(x.strip())}</div>' for x in block if x.strip()
                )
                body.append(f'<div class="refs">{inner}</div>')

            elif kind == "sources":
                body.append(
                    f'<div class="sources">{inline(" ".join(x.strip() for x in block if x.strip()))}</div>'
                )

            elif kind == "footer":
                body.append(
                    f'<div class="footer">{inline(" ".join(x.strip() for x in block if x.strip()))}</div>'
                )
            continue

        if ln.startswith("### "):
            body.append(f"<h3>{inline(ln[4:].strip())}</h3>")
            i += 1
            continue
        if ln.startswith("## "):
            body.append(f"<h2>{inline(ln[3:].strip())}</h2>")
            i += 1
            continue

        if ln.strip().startswith("|"):
            tbl = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            body.append(f'<div class="tablewrap">{table_html(tbl)}</div>')
            continue

        if not ln.strip():
            i += 1
            continue

        para = [ln.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#{1,3} |:::|\|)", lines[i]
        ):
            para.append(lines[i].strip())
            i += 1
        body.append(f"<p>{inline(' '.join(para))}</p>")

    _ = target
    head = f'<h1 class="title">{title}</h1>' + "".join(masthead)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{re.sub('<[^>]+>', '', title)}</title>"
        f"<style>{CSS}</style></head><body>"
        f'<div class="masthead">{head}</div>'
        f'<div class="body">{"".join(body)}</div>'
        "</body></html>"
    )


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if c and Path(c).exists():
            return c
    raise SystemExit("no Chrome/Chromium binary found for PDF rendering")


def publish() -> None:
    """Copy the rendered paper and its figures into the dashboard's public dir."""
    (PUBLISH_DIR / "figures").mkdir(parents=True, exist_ok=True)
    for f in (HTML_OUT, PDF_OUT):
        shutil.copy2(f, PUBLISH_DIR / f.name)
    for f in sorted((HERE / "figures").glob("*.png")):
        shutil.copy2(f, PUBLISH_DIR / "figures" / f.name)


def main() -> None:
    HTML_OUT.write_text(convert(SRC.read_text()), encoding="utf-8")
    chrome = find_chrome()
    subprocess.run(
        [
            chrome,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=10000",
            f"--print-to-pdf={PDF_OUT}",
            HTML_OUT.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    publish()
    print(
        f"wrote {HTML_OUT.name} and {PDF_OUT.name} "
        f"({PDF_OUT.stat().st_size // 1024} KB); published to "
        f"{PUBLISH_DIR.relative_to(HERE.parent)}/"
    )


if __name__ == "__main__":
    sys.exit(main())

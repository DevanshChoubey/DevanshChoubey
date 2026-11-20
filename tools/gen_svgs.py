"""Render the Matrix-style profile SVGs into assets/.

    python3 tools/gen_svgs.py                 # everything
    python3 tools/gen_svgs.py card            # only the neofetch card
    python3 tools/gen_svgs.py leaderboard     # only the leaderboard

Inputs: data/stats.json (written by tools/fetch_stats.py) and
data/leaderboard.json (written by tools/lint_issue.py). The SVGs use pure CSS
animation and no scripts, so they work inside a GitHub README <img>.
"""
import json
import random
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"

G = "#00ff41"    # phosphor green
G2 = "#00b32c"   # mid green
G3 = "#0a5c1f"   # dim green
WHITE = "#d6ffe0"
BG = "#000500"
RED = "#ff2a2a"
BLUE = "#2a7bff"
# ASCII only: these render in every monospace font, so the rain looks the same
# on every visitor's machine (katakana is missing on many Linux setups).
GLYPHS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ$#@%&*+=<>:;|/\\"
MONO = 'ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace'

DEFAULT_STATS = {
    "public_repos": None,
    "stars": None,
    "contributions": None,
    "releases": {},
}


def esc(value):
    return escape(str(value), quote=True)


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


# ---------------------------------------------------------------- shared parts
def rain(width, height, cols_step=22, seed=7, opacity=0.35, id_prefix="r"):
    """Columns of glyphs falling forever. Each column is one translated <text>."""
    rnd = random.Random(seed)
    css, els = [], []
    for i, x in enumerate(range(8, width, cols_step)):
        n = rnd.randint(10, 22)
        dur = rnd.uniform(5, 11)
        delay = -rnd.uniform(0, dur)
        cid = f"{id_prefix}{i}"
        css.append(f"#{cid}{{animation:fall {dur:.2f}s linear {delay:.2f}s infinite}}")
        tsp = []
        for j in range(n):
            ch = esc(rnd.choice(GLYPHS))
            if j == n - 1:  # bright head
                tsp.append(f'<tspan x="{x}" dy="18" fill="{WHITE}">{ch}</tspan>')
            else:
                op = round(0.15 + 0.85 * j / n, 2)
                tsp.append(f'<tspan x="{x}" dy="18" fill="{G}" fill-opacity="{op}">{ch}</tspan>')
        els.append(f'<text id="{cid}" y="{-n * 18}">{"".join(tsp)}</text>')
    css.append(f"@keyframes fall{{from{{transform:translateY(0)}}to{{transform:translateY({height + 450}px)}}}}")
    group = f'<g opacity="{opacity}" font-family=\'{MONO}\' font-size="15">{"".join(els)}</g>'
    return "\n".join(css), group


def svg(w, h, label, style, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">
<title>{esc(label)}</title>
<defs>
  <filter id="glow" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" fill-opacity="0.28"/></pattern>
  <linearGradient id="vig" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG}" stop-opacity="0.9"/><stop offset="0.25" stop-color="{BG}" stop-opacity="0"/><stop offset="0.8" stop-color="{BG}" stop-opacity="0"/><stop offset="1" stop-color="{BG}" stop-opacity="0.95"/></linearGradient>
</defs>
<style>
  .m{{font-family:{MONO}}}
  .g{{fill:{G}}}.g2{{fill:{G2}}}.g3{{fill:{G3}}}.w{{fill:{WHITE}}}
  {style}
  @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.seq{{opacity:1!important}}.bar{{transform:scaleX(1)!important}}}}
</style>
{body}
</svg>
"""


def frame(w, h, stroke=G3):
    return f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" fill="{BG}" stroke="{stroke}"/>'


def overlays(w, h):
    return (f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="10" fill="url(#vig)"/>'
            f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="10" fill="url(#scan)"/>')


# ---------------------------------------------------------------- hero
def hero():
    W, H, CYCLE, X = 880, 470, 16, 40
    rain_css, rain_g = rain(W, H, seed=3, opacity=0.55)

    steps = {"s4": 25, "s5": 34, "s6": 76, "s7": 79, "s8": 83,
             "s9": 86, "s10": 88, "s11": 90, "s12": 93}
    css = [rain_css]
    for cls, at in steps.items():
        css.append(f".{cls}{{animation:{cls} {CYCLE}s step-end infinite}}"
                   f"@keyframes {cls}{{0%{{opacity:0}}{at}%{{opacity:1}}97%{{opacity:0}}}}")
    for cls, (a, b) in {"t1": (2, 9), "t2": (12, 19), "t3": (22, 25)}.items():
        css.append(f".{cls}{{transform-box:fill-box;transform-origin:left center;animation:{cls} {CYCLE}s steps(28,end) infinite}}"
                   f"@keyframes {cls}{{0%,{a}%{{transform:scaleX(0)}}{b}%,97%{{transform:scaleX(1)}}100%{{transform:scaleX(0)}}}}")
    # shelllint takes 8% of the cycle, shellcheck 6.3x as long (50.4%)
    css.append(".bar{transform-box:fill-box;transform-origin:left center}"
               f"#fast{{animation:fast {CYCLE}s linear infinite}}#slow{{animation:slow {CYCLE}s linear infinite}}"
               "@keyframes fast{0%,26%{transform:scaleX(0)}34%,97%{transform:scaleX(1)}100%{transform:scaleX(0)}}"
               "@keyframes slow{0%,26%{transform:scaleX(0)}76.4%,97%{transform:scaleX(1)}100%{transform:scaleX(0)}}"
               ".cur{animation:blink 1s step-end infinite}@keyframes blink{50%{opacity:0}}")

    def typed(cls, y, text, size=24):
        return (f'<mask id="m{cls}"><rect class="{cls}" x="{X-4}" y="{y-size}" width="800" height="{size+10}" fill="#fff"/></mask>'
                f'<text x="{X}" y="{y}" class="m g" font-size="{size}" filter="url(#glow)" mask="url(#m{cls})">{esc(text)}</text>')

    def lint_row(cls, y, loc, code, sev, sevcls, msg):
        # explicit x columns, so alignment never depends on whitespace handling
        return (f'<g class="seq {cls} m" font-size="13.5">'
                f'<text x="{X}" y="{y}" class="g3">{loc}</text>'
                f'<text x="{X+110}" y="{y}" class="{sevcls}">{code} {sev}</text>'
                f'<text x="{X+260}" y="{y}" class="g2">{esc(msg)}</text></g>')

    body = f"""{frame(W, H)}
{rain_g}
<rect x="24" y="24" width="{W-48}" height="{H-48}" rx="8" fill="{BG}" fill-opacity="0.45"/>
{typed("t1", 72, "Wake up, Devansh...")}
{typed("t2", 108, "The shell scripts have you.")}
{typed("t3", 144, "Follow the fast linter.", 18)}
<g class="m" font-size="14">
  <text x="{X}" y="186" class="seq s4 g"><tspan class="w">$</tspan> lint-race --files 920</text>
  <g class="seq s4">
    <text x="{X}" y="220" class="g2">shellcheck</text>
    <circle cx="{X+108}" cy="215" r="5" fill="{BLUE}"/><text x="{X+118}" y="220" class="g3" font-size="12">blue pill</text>
    <rect x="{X+200}" y="208" width="520" height="14" fill="none" stroke="{G3}"/>
    <rect id="slow" class="bar" x="{X+200}" y="208" width="520" height="14" fill="{G3}"/>
    <text x="{X}" y="248" class="g" font-weight="700">shelllint</text>
    <circle cx="{X+108}" cy="243" r="5" fill="{RED}"/><text x="{X+118}" y="248" class="g2" font-size="12">red pill</text>
    <rect x="{X+200}" y="236" width="520" height="14" fill="none" stroke="{G3}"/>
    <rect id="fast" class="bar" x="{X+200}" y="236" width="520" height="14" fill="{G}" filter="url(#glow)"/>
  </g>
  <text x="{X+732}" y="249" class="seq s5 w">done</text>
  <text x="{X+732}" y="221" class="seq s6 g3">done</text>
  <text x="{X}" y="284" class="seq s7 g" filter="url(#glow)">&gt; 6.3x faster. Up to 20x less memory. Same SC codes.</text>
</g>
<path d="M{X} 308 H{W-X}" stroke="{G3}" stroke-dasharray="2 6"/>
<text x="{X}" y="338" class="seq s8 m g" font-size="14"><tspan class="w">$</tspan> radolint Dockerfile</text>
{lint_row("s9", 364, "Dockerfile:1", "DL3006", "warning", "g", "Always tag the version of an image explicitly")}
{lint_row("s10", 386, "Dockerfile:2", "DL3008", "warning", "g", "Pin versions in apt get install")}
{lint_row("s11", 408, "Dockerfile:2", "DL3015", "info", "g2", "Avoid additional packages: --no-install-recommends")}
<text x="{X}" y="440" class="seq s12 m g3" font-size="13"><tspan class="w">$</tspan> drop-in for hadolint. one ~10 MB binary, shellcheck built in<tspan class="cur g"> &#9608;</tspan></text>
{overlays(W, H)}"""
    return svg(W, H, "Wake up, Devansh. shelllint races shellcheck over 920 shell files and finishes 6.3 times faster, then radolint lints a Dockerfile.",
               "\n".join(css), body)


# ---------------------------------------------------------------- neofetch card
def fmt_int(n):
    return f"{n:,}" if isinstance(n, int) else "-"


def card(stats):
    W, H = 880, 340
    rain_css, rain_g = rain(260, H, cols_step=20, seed=11, opacity=0.45, id_prefix="n")
    D = ["11110", "10001", "10001", "10001", "10001", "10001", "11110"]
    C = ["01111", "10000", "10000", "10000", "10000", "10000", "01111"]
    px = [f'<rect x="{(ox+x)*16}" y="{y*16}" width="13" height="13"/>'
          for g, ox in ((D, 0), (C, 6))
          for y, row in enumerate(g)
          for x, c in enumerate(row) if c == "1"]
    rel = stats.get("releases") or {}
    latest = ", ".join(f"{name} {tag}" for name, tag in rel.items() if tag) or "-"
    rows = [
        ("Role", "Head of AI @ Kavida.ai"),
        ("Based", "Sagar, India"),
        ("Ships", "Rust linters, offline-first apps"),
        ("Langs", "Rust, TypeScript, Python"),
        ("Editor", "LSP + VS Code ext (radolint)"),
        None,
        ("Repos", fmt_int(stats.get("public_repos"))),
        ("Stars", fmt_int(stats.get("stars"))),
        ("Contribs", f"{fmt_int(stats.get('contributions'))} in the last year"),
        ("Releases", latest),
    ]
    kx, vx, y, lines = 320, 440, 84, []
    for r in rows:
        if r is None:
            lines.append(f'<text x="{kx}" y="{y}" class="g3">-- github {"-" * 38}</text>')
        else:
            lines.append(f'<text x="{kx}" y="{y}" class="g" font-weight="700">{esc(r[0])}</text>'
                         f'<text x="{vx}" y="{y}" class="g2">{esc(r[1])}</text>')
        y += 22
    updated = esc(stats.get("updated", ""))
    body = f"""{frame(W, H)}
<clipPath id="lc"><rect x="1" y="1" width="280" height="{H-2}" rx="10"/></clipPath>
<g clip-path="url(#lc)">{rain_g}</g>
<rect x="56" y="88" width="190" height="140" fill="{BG}" fill-opacity="0.7"/>
<g transform="translate(64 98)" fill="{G}" filter="url(#glow)">{"".join(px)}</g>
<path d="M280 20 V{H-20}" stroke="{G3}"/>
<g class="m" font-size="14">
  <text x="{kx}" y="44" class="w">devansh@mainframe:~$ <tspan class="g">neofetch</tspan></text>
  <text x="{kx}" y="64" class="g3">{"-" * 48}</text>
  {"".join(lines)}
  <text x="{kx}" y="{H-18}" class="g3" font-size="12">refreshed daily{(" · " + updated) if updated else ""}</text>
</g>
{overlays(W, H)}"""
    return svg(W, H, "Devansh Choubey: Head of AI at Kavida.ai. Rust linters and offline-first apps.", rain_css, body)


# ---------------------------------------------------------------- leaderboard
def leaderboard(board):
    total = board.get("total", 0) if isinstance(board.get("total"), int) else 0
    codes = board.get("codes") or {}
    top = sorted(((c, n) for c, n in codes.items() if isinstance(n, int) and n > 0),
                 key=lambda kv: (-kv[1], kv[0]))[:6]
    W = 880
    if not top or total <= 0:
        H = 150
        body = f"""{frame(W, H)}
<g class="m" font-size="14">
  <text x="40" y="44" class="w">$ grep -c anomalies /construct/*.Dockerfile</text>
  <text x="40" y="84" class="g" font-size="18" filter="url(#glow)">0 Dockerfiles scanned. The construct is empty.</text>
  <text x="40" y="116" class="g2">Be the first: take the red pill and paste a Dockerfile.</text>
</g>
{overlays(W, H)}"""
        return svg(W, H, "No Dockerfiles scanned yet. Be the first.", "", body)

    H = 84 + 34 * len(top) + 20
    out, y = [], 100
    for code, n in top:
        pct = round(100 * n / total)
        out.append(f'<text x="40" y="{y}" class="g" font-weight="700">{esc(code)}</text>'
                   f'<text x="130" y="{y}" class="g2">{n} of {total}</text>'
                   f'<rect x="260" y="{y-12}" width="520" height="14" fill="none" stroke="{G3}"/>'
                   f'<rect x="260" y="{y-12}" width="{max(2, round(5.2 * pct))}" height="14" fill="{G}" filter="url(#glow)"/>'
                   f'<text x="796" y="{y}" class="w" font-size="12">{pct}%</text>')
        y += 34
    noun = "Dockerfile" if total == 1 else "Dockerfiles"
    body = f"""{frame(W, H)}
<g class="m" font-size="14">
  <text x="40" y="44" class="w">$ grep -c anomalies /construct/*.Dockerfile</text>
  <text x="40" y="66" class="g3" font-size="12">most common findings across {total} {noun} visitors pasted in</text>
  {"".join(out)}
</g>
{overlays(W, H)}"""
    return svg(W, H, f"Most common radolint findings across {total} visitor {noun}", "", body)


# ---------------------------------------------------------------- red pill button
def pill():
    W, H = 440, 56
    style = ".pulse{animation:p 2.4s ease-in-out infinite}@keyframes p{50%{opacity:.55}}"
    body = f"""<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="28" fill="{BG}" stroke="{RED}" stroke-width="1.5"/>
<rect class="pulse" x="1" y="1" width="{W-2}" height="{H-2}" rx="28" fill="none" stroke="{RED}" stroke-width="5" stroke-opacity=".35" filter="url(#glow)"/>
<g transform="translate(34 28) rotate(-35)"><rect x="-16" y="-8" width="32" height="16" rx="8" fill="{RED}" filter="url(#glow)"/><rect x="-16" y="-8" width="16" height="16" rx="8" fill="#b30000"/></g>
<text x="66" y="34" class="m" font-size="16" fill="#ffd6d6" font-weight="700">Take the red pill: lint a Dockerfile</text>"""
    return svg(W, H, "Take the red pill: lint a Dockerfile", style, body)


def main(argv):
    stats = {**DEFAULT_STATS, **load_json(DATA / "stats.json", {})}
    board = load_json(DATA / "leaderboard.json", {"total": 0, "codes": {}})
    targets = {
        "hero": ("matrix-hero.svg", hero),
        "card": ("neofetch.svg", lambda: card(stats)),
        "leaderboard": ("leaderboard.svg", lambda: leaderboard(board)),
        "pill": ("red-pill.svg", pill),
    }
    wanted = argv or list(targets)
    unknown = [t for t in wanted if t not in targets]
    if unknown:
        sys.exit(f"unknown target(s): {', '.join(unknown)}; choose from {', '.join(targets)}")
    ASSETS.mkdir(exist_ok=True)
    for t in wanted:
        name, fn = targets[t]
        (ASSETS / name).write_text(fn(), encoding="utf-8")
        print("wrote", f"assets/{name}")


if __name__ == "__main__":
    main(sys.argv[1:])

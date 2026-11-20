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
# An illustrative agent trace (the same one as on the resume), replayed as a
# Matrix terminal: each span's bar grows over its real share of the 4.1 s run.
TRACE = [
    # (depth, name, start_ms, dur_ms, badge)
    (0, "email.received", 0, 12, None),
    (1, "classify_document", 12, 640, None),
    (1, "extract.order_ack", 652, 2100, None),
    (1, "po_updater.diff", 2752, 910, None),
    (1, "schema_check", 3662, 38, "pass"),
    (1, "eval.golden_set", 3700, 410, "pass"),
    (0, "erp.sync", 4110, 0, "buyer approves"),
]
TRACE_MS = 4110


def hero():
    W, H, CYCLE, X = 880, 480, 16, 40
    rain_css, rain_g = rain(W, H, seed=3, opacity=0.5)
    css = [rain_css]

    def appear(cls, at):
        css.append(f".{cls}{{animation:{cls} {CYCLE}s step-end infinite}}"
                   f"@keyframes {cls}{{0%{{opacity:0}}{at:.2f}%{{opacity:1}}97%{{opacity:0}}}}")

    for cls, (a, b) in {"t1": (2, 9), "t2": (11, 17), "t3": (19, 24)}.items():
        css.append(f".{cls}{{transform-box:fill-box;transform-origin:left center;animation:{cls} {CYCLE}s steps(28,end) infinite}}"
                   f"@keyframes {cls}{{0%,{a}%{{transform:scaleX(0)}}{b}%,97%{{transform:scaleX(1)}}100%{{transform:scaleX(0)}}}}")
    css.append(".bar{transform-box:fill-box;transform-origin:left center}"
               ".cur{animation:blink 1s step-end infinite}@keyframes blink{50%{opacity:0}}")

    # trace replay window inside the cycle
    T0, T1 = 30.0, 72.0
    def pct(ms):
        return T0 + (T1 - T0) * ms / TRACE_MS

    appear("hdr", 26)
    BX, BW = X + 330, 380          # waterfall area
    rows, y = [], 214
    for i, (depth, name, start, dur, badge) in enumerate(TRACE):
        cls = f"row{i}"
        a = pct(start)
        b = max(pct(start + dur), a + 0.8)
        appear(cls, a)
        label = ("&#9492; " if depth else "") + esc(name)
        bx = BX + BW * start / TRACE_MS
        bw = max(3, BW * dur / TRACE_MS)
        bar = ""
        if dur:
            css.append(f"#bar{i}{{animation:bar{i} {CYCLE}s linear infinite}}"
                       f"@keyframes bar{i}{{0%,{a:.2f}%{{transform:scaleX(0)}}{b:.2f}%,97%{{transform:scaleX(1)}}100%{{transform:scaleX(0)}}}}")
            bar = (f'<rect x="{BX}" y="{y-11}" width="{BW}" height="12" fill="{G}" fill-opacity="0.06"/>'
                   f'<rect id="bar{i}" class="bar" x="{bx:.1f}" y="{y-11}" width="{bw:.1f}" height="12" fill="{G if name.startswith("extract") else G2}" filter="url(#glow)"/>')
        timing = f"{dur / 1000:.1f}s" if dur >= 1000 else (f"{dur}ms" if dur else "&#8212;")
        appear(f"done{i}", b)
        badge_svg = ""
        if badge:
            color = G if badge == "pass" else "#ffb000"
            bw2 = 8.6 * len(badge) + 12
            badge_svg = (f'<g class="done{i}"><rect x="{X+190}" y="{y-12}" width="{bw2:.0f}" height="16" rx="3" fill="none" stroke="{color}"/>'
                         f'<text x="{X+196}" y="{y}" font-size="12" fill="{color}">{esc(badge)}</text></g>')
        rows.append(f'<g class="{cls}"><text x="{X + (14 if depth else 0)}" y="{y}" class="{"w" if depth == 0 else "g"}">{label}</text>{bar}'
                    f'<text x="{BX + BW + 64}" y="{y}" class="g2 done{i}" text-anchor="end">{timing}</text></g>{badge_svg}')
        y += 26
    appear("total", T1)
    appear("tag1", 76)
    appear("tag2", 80)

    body = f"""{frame(W, H)}
{rain_g}
<rect x="24" y="24" width="{W-48}" height="{H-48}" rx="8" fill="{BG}" fill-opacity="0.5"/>
<mask id="mt1"><rect class="t1" x="{X-4}" y="48" width="800" height="34" fill="#fff"/></mask>
<text x="{X}" y="72" class="m g" font-size="24" filter="url(#glow)" mask="url(#mt1)">Wake up, Devansh...</text>
<mask id="mt2"><rect class="t2" x="{X-4}" y="84" width="800" height="34" fill="#fff"/></mask>
<text x="{X}" y="108" class="m g" font-size="24" filter="url(#glow)" mask="url(#mt2)">The supply chain runs on email.</text>
<mask id="mt3"><rect class="t3" x="{X-4}" y="124" width="800" height="28" fill="#fff"/></mask>
<text x="{X}" y="144" class="m g" font-size="18" filter="url(#glow)" mask="url(#mt3)">Follow the agents.</text>
<g class="m" font-size="14">
  <g class="hdr"><text x="{X}" y="184" class="w">$ trace supplier_update <tspan class="g2" font-size="12">  # illustrative</tspan></text>
  <path d="M{X} 196 H{W-X}" stroke="{G3}" stroke-dasharray="2 6"/></g>
  {"".join(rows)}
  <text x="{W-X}" y="184" class="total w" text-anchor="end">4.1s</text>
  <text x="{X}" y="420" class="tag1 g" font-size="18" filter="url(#glow)">&gt; I build AI agents that do real operations work.</text>
  <text x="{X}" y="448" class="tag2 g2" font-size="13">every step evaluated, traced and costed. in production for 10+ enterprise clients<tspan class="cur g"> &#9608;</tspan></text>
</g>
{overlays(W, H)}"""
    return svg(W, H, "Wake up, Devansh. An illustrative agent trace: a supplier email is classified, the order acknowledgement extracted, the PO diffed, schema-checked and evaluated, then synced to the ERP after the buyer approves. I build AI agents that do real operations work.",
               "\n".join(css), body)


# ---------------------------------------------------------------- origin story
# Why: the Matrix, then Agent Smith boots.
def origin():
    W, H, CYCLE, X = 880, 500, 18, 40
    rain_css, rain_g = rain(W, H, seed=3, opacity=0.5)
    css = [rain_css,
           ".bar{transform-box:fill-box;transform-origin:left center}"
           ".cur{animation:blink 1s step-end infinite}@keyframes blink{50%{opacity:0}}"]

    def appear(cls, at):
        css.append(f".{cls}{{animation:{cls} {CYCLE}s step-end infinite}}"
                   f"@keyframes {cls}{{0%{{opacity:0}}{at:.2f}%{{opacity:1}}97%{{opacity:0}}}}")

    typed_lines = [  # (cls, y, size, text, start%, end%)
        ("t1", 70, 24, "Wake up, Devansh...", 2, 8),
        ("t2", 104, 18, "You watched The Matrix and never got over it.", 10, 17),
        ("t3", 132, 18, "You had no idea how hard it is to build one.", 19, 26),
        ("t4", 160, 18, "You started anyway.", 28, 31),
    ]
    typed = []
    for cls, y, size, text, a, b in typed_lines:
        css.append(f".{cls}{{transform-box:fill-box;transform-origin:left center;animation:{cls} {CYCLE}s steps(36,end) infinite}}"
                   f"@keyframes {cls}{{0%,{a}%{{transform:scaleX(0)}}{b}%,97%{{transform:scaleX(1)}}100%{{transform:scaleX(0)}}}}")
        typed.append(f'<mask id="m{cls}"><rect class="{cls}" x="{X-4}" y="{y-size-4}" width="800" height="{size+12}" fill="#fff"/></mask>'
                     f'<text x="{X}" y="{y}" class="m g" font-size="{size}" filter="url(#glow)" mask="url(#m{cls})">{esc(text)}</text>')

    # boot log: (status, label, value, appear%)
    boot = [
        ("ok", "loading perspective", "different", 40),
        ("ok", "loading will_of_fire", None, 45),          # value is a filling bar
        ("ok", "scanning problems", "every one has a solution", 56),
        ("ok", "spawning agents", "supplier_update, po_tracker, copilot", 61),
        ("..", "mission: save the world", "in progress", 66),
    ]
    appear("cmd", 35)
    rows, y = [], 238
    for i, (status, label, value, at) in enumerate(boot):
        cls = f"b{i}"
        appear(cls, at)
        scol = "g" if status == "ok" else "w"
        val = ""
        if value is None:
            css.append(f"#fire{{animation:fire {CYCLE}s linear infinite}}"
                       f"@keyframes fire{{0%,{at}%{{transform:scaleX(0)}}{at+8}%,97%{{transform:scaleX(1)}}100%{{transform:scaleX(0)}}}}")
            appear("firepct", at + 8)
            val = (f'<rect x="{X+430}" y="{y-11}" width="260" height="12" fill="none" stroke="{G3}"/>'
                   f'<rect id="fire" class="bar" x="{X+430}" y="{y-11}" width="260" height="12" fill="{G}" filter="url(#glow)"/>'
                   f'<text x="{X+700}" y="{y}" class="w firepct">100%</text>')
        else:
            val = f'<text x="{X+430}" y="{y}" class="{"w" if status == ".." else "g2"}">{esc(value)}</text>'
        rows.append(f'<g class="{cls}"><text x="{X}" y="{y}" class="{scol}">[{status:^4}]</text>'
                    f'<text x="{X+70}" y="{y}" class="g">{esc(label)}</text>'
                    f'<path d="M{X+70 + 8.4*len(label) + 10:.0f} {y-4} H{X+418}" stroke="{G3}" stroke-dasharray="1 5"/>'
                    f'{val}</g>')
        y += 26
    appear("q1", 76)
    appear("q2", 82)

    body = f"""{frame(W, H)}
{rain_g}
<rect x="24" y="24" width="{W-48}" height="{H-48}" rx="8" fill="{BG}" fill-opacity="0.5"/>
{"".join(typed)}
<g class="m" font-size="14">
  <text x="{X}" y="204" class="cmd w">$ ./agent_smith --mission "save the world"</text>
  {"".join(rows)}
  <text x="{X}" y="420" class="q1 g" font-size="18" filter="url(#glow)">&gt; Every problem has a solution.</text>
  <text x="{X}" y="452" class="q2 g" font-size="18" filter="url(#glow)">&gt; All it takes is a different perspective and the will of fire.<tspan class="cur"> &#9608;</tspan></text>
</g>
{overlays(W, H)}"""
    return svg(W, H, "Wake up, Devansh. You watched The Matrix and never got over it. You had no idea how hard it is to build one. You started anyway. Agent Smith boots with the mission: save the world. Every problem has a solution. All it takes is a different perspective and the will of fire.",
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
    rows = [
        ("Mission", "build intelligent machines that help"),
        ("Origin", "The Matrix, as a teenager"),
        ("Believes", "every problem has a solution"),
        ("Fuel", "a different perspective + the will of fire"),
        ("Days", "AI agents for real operations @ QAD"),
        ("Nights", "Rust dev tools, offline-first remotes"),
        ("Based", "Hyderabad, India"),
        None,
        ("Repos", fmt_int(stats.get("public_repos"))),
        ("Contribs", f"{fmt_int(stats.get('contributions'))} in the last year"),
    ]
    kx, vx, y, lines = 320, 430, 84, []
    for r in rows:
        if r is None:
            lines.append(f'<text x="{kx}" y="{y}" class="g3">-- github {"-" * 40}</text>')
        else:
            lines.append(f'<text x="{kx}" y="{y}" class="g" font-weight="700">{esc(r[0])}</text>'
                         f'<text x="{vx}" y="{y}" class="g2">{esc(r[1])}</text>')
        y += 23
    body = f"""{frame(W, H)}
<clipPath id="lc"><rect x="1" y="1" width="280" height="{H-2}" rx="10"/></clipPath>
<g clip-path="url(#lc)">{rain_g}</g>
<rect x="56" y="98" width="190" height="140" fill="{BG}" fill-opacity="0.7"/>
<g transform="translate(64 108)" fill="{G}" filter="url(#glow)">{"".join(px)}</g>
<path d="M280 20 V{H-20}" stroke="{G3}"/>
<g class="m" font-size="14">
  <text x="{kx}" y="44" class="w">devansh@zion:~$ <tspan class="g">neofetch</tspan></text>
  <text x="{kx}" y="64" class="g3">{"-" * 50}</text>
  {"".join(lines)}
</g>
{overlays(W, H)}"""
    return svg(W, H, "Devansh Choubey. Mission: build intelligent machines that help. Origin: The Matrix. Believes every problem has a solution. Days: AI agents at QAD. Nights: Rust dev tools and offline-first remotes.",
               rain_css, body)


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
        "origin": ("origin.svg", origin),
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

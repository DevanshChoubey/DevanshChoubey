"""The "red pill" bot: lint a Dockerfile pasted into an issue.

Everything in the issue is untrusted. The body is read from the event file
(never interpolated into a shell), radolint only parses it (nothing is run),
the reply fences all echoed text so it cannot break out of a code block or
ping anyone, and only rule codes matching CODE_RE ever reach the leaderboard.

    python3 tools/lint_issue.py lint --event "$GITHUB_EVENT_PATH" --radolint ./radolint --out out
    python3 tools/lint_issue.py apply out/result.json      # bump data/leaderboard.json
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "data" / "leaderboard.json"

MAX_CHARS = 20_000
MAX_LINES = 400
MAX_SHOWN = 50
CODE_RE = re.compile(r"^(DL|SC)\d{4}$")
PARSE_ERROR = "DL1000"
HEADING = "### Dockerfile"
ACTION_REF = "DevanshChoubey/radolint@v0.3.0"


class Rejected(Exception):
    """The issue cannot be linted; the message is safe to show the author."""


def extract(body):
    """Return the Dockerfile text from an issue-form body, or raise Rejected."""
    if not body:
        raise Rejected("The issue is empty. Paste a Dockerfile into the form.")
    text = body.replace("\r\n", "\n").replace("\r", "\n")
    if len(text) > MAX_CHARS:
        raise Rejected(f"That is over {MAX_CHARS:,} characters. Paste a single, smaller Dockerfile.")

    # Issue forms render as "### Dockerfile\n\n```dockerfile\n...\n```".
    # Take everything after the heading: the form has one field, and a
    # Dockerfile may itself contain "### comment" lines.
    idx = text.find(HEADING)
    if idx != -1:
        text = text[idx + len(HEADING):]

    lines = text.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and lines[0].lstrip().startswith("```"):
        lines.pop(0)
        if lines and re.fullmatch(r"\s*`{3,}\s*", lines[-1]):
            lines.pop()

    dockerfile = "\n".join(lines).strip("\n")
    if not dockerfile.strip() or dockerfile.strip() == "_No response_":
        raise Rejected("No Dockerfile found. Paste one into the form's Dockerfile box.")
    if len(lines) > MAX_LINES:
        raise Rejected(f"That is over {MAX_LINES} lines. Paste a single, smaller Dockerfile.")
    return dockerfile + "\n"


def run_radolint(dockerfile, binary, timeout=20):
    proc = subprocess.run(
        [binary, "--format", "json", "--no-fail", "-"],
        input=dockerfile, capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"radolint exited {proc.returncode}: {proc.stderr[:500]}")
    findings = json.loads(proc.stdout or "[]")
    if not isinstance(findings, list):
        raise RuntimeError("radolint returned unexpected JSON")
    return findings


def fence(text):
    """Wrap text in a code fence longer than any backtick run inside it."""
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}text\n{text}\n{ticks}"


def rule_link(code):
    if not CODE_RE.match(code):
        return None
    if code.startswith("SC"):
        return f"[{code}](https://www.shellcheck.net/wiki/{code})"
    return f"[{code}](https://github.com/hadolint/hadolint/wiki/{code})"


def render_comment(findings):
    if not findings:
        return ("### > 0 anomalies detected\n\n"
                "radolint found nothing to fix. This Dockerfile is clean. Welcome to the real world.\n\n"
                + footer())

    if any(f.get("code") == PARSE_ERROR for f in findings):
        msg = next(f for f in findings if f.get("code") == PARSE_ERROR)
        return ("### > the construct could not load this file\n\n"
                "radolint could not parse it as a Dockerfile:\n\n"
                + fence(str(msg.get("message", "")).strip()[:600]) + "\n\n" + footer())

    levels = {}
    for f in findings:
        levels[f.get("level", "?")] = levels.get(f.get("level", "?"), 0) + 1
    summary = ", ".join(f"{n} {lvl}" for lvl, n in sorted(levels.items(), key=lambda kv: -kv[1]))

    rows = []
    for f in findings[:MAX_SHOWN]:
        code = str(f.get("code", ""))
        rows.append(f"line {f.get('line', '?'):<4} {code:<7} {str(f.get('level', '')):<8} {f.get('message', '')}")
    if len(findings) > MAX_SHOWN:
        rows.append(f"... and {len(findings) - MAX_SHOWN} more")

    codes = sorted({str(f.get("code", "")) for f in findings})
    links = " · ".join(link for link in map(rule_link, codes) if link)
    n = len(findings)
    return (f"### > {n} {'anomaly' if n == 1 else 'anomalies'} detected ({summary})\n\n"
            + fence("\n".join(rows)) + "\n\n"
            + (f"Rule docs: {links}\n\n" if links else "")
            + footer())


def footer():
    return ("---\n"
            "Linted by [radolint](https://github.com/DevanshChoubey/radolint), a Rust drop-in for hadolint. "
            "It only parsed your file; nothing was run. To check every pull request, add it to CI:\n\n"
            f"```yaml\n- uses: {ACTION_REF}\n  with:\n    dockerfile: Dockerfile\n```\n\n"
            "_This issue closes itself. Your findings now count toward the leaderboard on the profile._")


def board_codes(findings):
    """Codes that may enter the leaderboard: valid shape, unique, no parse errors."""
    if any(f.get("code") == PARSE_ERROR for f in findings):
        return None
    return sorted({c for c in (str(f.get("code", "")) for f in findings) if CODE_RE.match(c)})


def apply_result(board, result):
    if not result.get("counted"):
        return board
    codes = board.setdefault("codes", {})
    board["total"] = int(board.get("total", 0)) + 1
    for code in result.get("codes", []):
        if CODE_RE.match(code):
            codes[code] = int(codes.get(code, 0)) + 1
    board["codes"] = dict(sorted(codes.items()))
    return board


def cmd_lint(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    event = json.loads(Path(args.event).read_text(encoding="utf-8"))
    body = (event.get("issue") or {}).get("body")
    result = {"counted": False, "codes": []}
    try:
        dockerfile = extract(body)
        findings = run_radolint(dockerfile, args.radolint)
        comment = render_comment(findings)
        codes = board_codes(findings)
        if codes is not None:
            result = {"counted": True, "codes": codes}
    except Rejected as e:
        comment = f"### > the construct rejected this request\n\n{e}\n\n{footer()}"
    (out / "comment.md").write_text(comment, encoding="utf-8")
    (out / "result.json").write_text(json.dumps(result) + "\n", encoding="utf-8")
    print(json.dumps(result))


def cmd_apply(args):
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    try:
        board = json.loads(BOARD.read_text(encoding="utf-8"))
    except FileNotFoundError:
        board = {"total": 0, "codes": {}}
    board = apply_result(board, result)
    BOARD.write_text(json.dumps(board, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(board))


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    lint = sub.add_parser("lint")
    lint.add_argument("--event", required=True)
    lint.add_argument("--radolint", required=True)
    lint.add_argument("--out", required=True)
    apply = sub.add_parser("apply")
    apply.add_argument("result")
    args = p.parse_args(argv)
    {"lint": cmd_lint, "apply": cmd_apply}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

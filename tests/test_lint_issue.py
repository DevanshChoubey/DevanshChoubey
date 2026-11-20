"""Tests for the red-pill bot. Run: python3 -m unittest discover -s tests

Tests that need the real binary use RADOLINT=/path/to/radolint and are
skipped when it is not set.
"""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import lint_issue as li  # noqa: E402

FORM = "### Dockerfile\n\n```dockerfile\n{}\n```\n"
RADOLINT = os.environ.get("RADOLINT")


def form(text):
    return FORM.format(text)


class Extract(unittest.TestCase):
    def test_issue_form_wrapper(self):
        self.assertEqual(li.extract(form("FROM alpine:3.20\nRUN echo hi")), "FROM alpine:3.20\nRUN echo hi\n")

    def test_crlf(self):
        body = form("FROM alpine:3.20\nRUN echo hi").replace("\n", "\r\n")
        self.assertEqual(li.extract(body), "FROM alpine:3.20\nRUN echo hi\n")

    def test_empty_and_none(self):
        for body in (None, "", "   ", form(""), "### Dockerfile\n\n_No response_\n"):
            with self.assertRaises(li.Rejected):
                li.extract(body)

    def test_oversized(self):
        with self.assertRaises(li.Rejected):
            li.extract(form("RUN echo x\n" * 3000))

    def test_too_many_lines(self):
        with self.assertRaises(li.Rejected):
            li.extract(form("\n".join(["RUN true"] * (li.MAX_LINES + 5))))

    def test_hash_comments_survive(self):
        df = "FROM alpine:3.20\n### build stage\nRUN echo hi"
        self.assertIn("### build stage", li.extract(form(df)))

    def test_body_with_inner_fence_keeps_content(self):
        df = "FROM alpine:3.20\nRUN echo '```'"
        self.assertIn("RUN echo '```'", li.extract(form(df)))

    def test_plain_body_without_form(self):
        self.assertEqual(li.extract("FROM alpine:3.20\n"), "FROM alpine:3.20\n")

    def test_shell_metacharacters_are_just_text(self):
        df = "FROM alpine:3.20\nRUN echo $(rm -rf /) `whoami` ; @someone"
        self.assertIn("$(rm -rf /)", li.extract(form(df)))


class Render(unittest.TestCase):
    def test_fence_longer_than_content_backticks(self):
        out = li.fence("a ```` b")
        self.assertTrue(out.startswith("`````text\n"))
        self.assertTrue(out.endswith("\n`````"))

    def test_mentions_stay_inside_fence(self):
        findings = [{"code": "DL1000", "level": "error", "line": 1,
                     "message": "unexpected '@'\n@everyone ```` @someone"}]
        comment = li.render_comment(findings)
        # every @mention must be inside the fenced block
        m = re.search(r"(`{3,})text\n(.*?)\n\1", comment, re.S)
        self.assertIsNotNone(m)
        outside = comment.replace(m.group(0), "")
        self.assertNotIn("@everyone", outside)
        self.assertNotIn("@someone", outside)

    def test_clean_file(self):
        self.assertIn("0 anomalies", li.render_comment([]))

    def test_rule_links_only_for_valid_codes(self):
        self.assertIsNone(li.rule_link("DL3006](javascript:alert(1))"))
        self.assertIn("hadolint/wiki/DL3006", li.rule_link("DL3006"))
        self.assertIn("shellcheck.net/wiki/SC2086", li.rule_link("SC2086"))

    def test_caps_listed_findings(self):
        findings = [{"code": "DL3008", "level": "warning", "line": i, "message": "x"} for i in range(80)]
        self.assertIn("and 30 more", li.render_comment(findings))


class Board(unittest.TestCase):
    def test_only_valid_codes_counted(self):
        findings = [{"code": "DL3006"}, {"code": "DL3006"}, {"code": "<script>"}, {"code": "SC2086"}, {"code": "DL30061"}]
        self.assertEqual(li.board_codes(findings), ["DL3006", "SC2086"])

    def test_parse_error_not_counted(self):
        self.assertIsNone(li.board_codes([{"code": "DL1000"}, {"code": "DL3006"}]))

    def test_apply(self):
        board = {"total": 2, "codes": {"DL3006": 1}}
        board = li.apply_result(board, {"counted": True, "codes": ["DL3006", "DL3008", "bad"]})
        self.assertEqual(board, {"total": 3, "codes": {"DL3006": 2, "DL3008": 1}})
        self.assertEqual(li.apply_result(board, {"counted": False, "codes": ["DL3006"]})["total"], 3)


@unittest.skipUnless(RADOLINT, "set RADOLINT=/path/to/radolint")
class EndToEnd(unittest.TestCase):
    def run_lint(self, body):
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d) / "event.json"
            ev.write_text(json.dumps({"issue": {"body": body}}))
            li.main(["lint", "--event", str(ev), "--radolint", RADOLINT, "--out", d])
            return (Path(d) / "comment.md").read_text(), json.loads((Path(d) / "result.json").read_text())

    def test_real_findings(self):
        comment, result = self.run_lint(form("FROM ubuntu\nRUN apt-get update && apt-get install curl"))
        self.assertTrue(result["counted"])
        self.assertIn("DL3006", result["codes"])
        self.assertIn("anomalies detected", comment)

    def test_garbage_is_parse_error_not_counted(self):
        comment, result = self.run_lint(form("hello @everyone $(id)"))
        self.assertFalse(result["counted"])
        self.assertIn("could not parse", comment)

    def test_rejected_is_not_counted(self):
        comment, result = self.run_lint("")
        self.assertFalse(result["counted"])
        self.assertIn("rejected", comment)
        self.assertNotIn("leaderboard", comment)

    def test_counted_reply_mentions_leaderboard(self):
        comment, _ = self.run_lint(form("FROM ubuntu"))
        self.assertIn("leaderboard", comment)


class Failure(unittest.TestCase):
    def test_broken_binary_still_replies(self):
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d) / "event.json"
            ev.write_text(json.dumps({"issue": {"body": form("FROM alpine:3.20")}}))
            li.main(["lint", "--event", str(ev), "--radolint", "/nonexistent/radolint", "--out", d])
            comment = (Path(d) / "comment.md").read_text()
            result = json.loads((Path(d) / "result.json").read_text())
        self.assertIn("glitch", comment)
        self.assertFalse(result["counted"])


if __name__ == "__main__":
    unittest.main()

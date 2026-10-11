import contextlib
import io
import json
import os
import tempfile
import unittest

from envguard import cli
from envguard.checks import looks_like_secret, run_checks
from envguard.parser import parse_env

SECRET = "sup3rS3cretValueDoNotLeak42"


def codes(findings):
    return sorted(f.code for f in findings)


class ParserTests(unittest.TestCase):
    def test_basic_comments_blank_export(self):
        r = parse_env("# c\n\nA=1\nexport B=two\n")
        self.assertEqual(r.values, {"A": "1", "B": "two"})
        self.assertEqual(r.lines, {"A": 3, "B": 4})
        self.assertEqual(r.issues, [])

    def test_inline_comment_unquoted(self):
        self.assertEqual(parse_env("A=x #note").values["A"], "x")
        self.assertEqual(parse_env("A=x#notcomment").values["A"], "x#notcomment")

    def test_single_quotes_literal(self):
        self.assertEqual(parse_env(r"A='a\nb # c'").values["A"], r"a\nb # c")

    def test_double_quote_escapes(self):
        r = parse_env(r'A="l1\nl2 \"q\" \\ end"')
        self.assertEqual(r.values["A"], 'l1\nl2 "q" \\ end')

    def test_value_may_contain_equals(self):
        self.assertEqual(parse_env("URL=a=b=c").values["URL"], "a=b=c")

    def test_malformed(self):
        r = parse_env("NOEQUALS\n1BAD=x\nQ=\"open\n")
        self.assertEqual([i.code for i in r.issues], ["malformed"] * 3)
        self.assertEqual([i.line for i in r.issues], [1, 2, 3])
        self.assertEqual(r.values, {})

    def test_duplicate_last_wins(self):
        r = parse_env("A=1\nA=2\n")
        self.assertEqual(r.values["A"], "2")
        self.assertEqual(r.lines["A"], 2)
        self.assertEqual(codes(r.issues), ["duplicate"])
        self.assertEqual(r.issues[0].severity, "warning")


class CheckTests(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(run_checks(parse_env("A=1"), parse_env("A=")), [])

    def test_missing_extra_empty(self):
        env = parse_env("B=\nC=3\n")
        ex = parse_env("A=x\nB=y\n")
        f = run_checks(env, ex)
        self.assertEqual(codes(f), ["empty", "extra", "missing"])
        self.assertEqual([x.severity for x in f], ["error", "error", "warning"])

    def test_empty_allowed_when_example_empty(self):
        self.assertEqual(run_checks(parse_env("A="), parse_env("A=")), [])

    def test_example_secret(self):
        f = run_checks(parse_env(f"K={SECRET}"), parse_env(f"K={SECRET}"))
        self.assertEqual(codes(f), ["example-secret"])

    def test_secret_heuristic(self):
        self.assertTrue(looks_like_secret("sk_live_x"))
        self.assertTrue(looks_like_secret("ghp_abc"))
        self.assertTrue(looks_like_secret("AKIAXXXX"))
        self.assertTrue(looks_like_secret(SECRET))
        self.assertFalse(looks_like_secret("changeme"))
        self.assertFalse(looks_like_secret("a" * 30))
        self.assertFalse(looks_like_secret("postgres://localhost:5432/app_db"))

    def test_parser_issues_included_from_both_files(self):
        f = run_checks(parse_env("BAD\nA=1"), parse_env("A=\nA=\n"))
        self.assertEqual(codes(f), ["duplicate", "malformed"])
        self.assertTrue(any("(in example)" in x.message for x in f))


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_exit_0(self):
        e = self.write(".env", f"A={SECRET}\n")
        x = self.write(".env.example", "A=\n")
        code, out, _ = self.run_cli("--env", e, "--example", x)
        self.assertEqual(code, 0)
        self.assertIn("0 error(s), 0 warning(s)", out)

    def test_exit_1_on_error(self):
        e = self.write(".env", f"B={SECRET}\n")
        x = self.write(".env.example", "A=\nB=\n")
        code, out, _ = self.run_cli("--env", e, "--example", x)
        self.assertEqual(code, 1)
        self.assertIn("ERROR missing A", out)

    def test_exit_2_missing_file(self):
        x = self.write(".env.example", "A=\n")
        code, _, err = self.run_cli("--env", os.path.join(self.tmp.name, "nope"),
                                    "--example", x)
        self.assertEqual(code, 2)
        self.assertIn("cannot read env file", err)

    def test_strict_fails_on_warning(self):
        e = self.write(".env", "A=1\nEXTRA=2\n")
        x = self.write(".env.example", "A=\n")
        self.assertEqual(self.run_cli("--env", e, "--example", x)[0], 0)
        self.assertEqual(self.run_cli("--env", e, "--example", x, "--strict")[0], 1)

    def test_json_format(self):
        e = self.write(".env", "EXTRA=1\n")
        x = self.write(".env.example", "A=\n")
        code, out, _ = self.run_cli("--env", e, "--example", x, "--format", "json")
        data = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual((data["errors"], data["warnings"]), (1, 1))
        self.assertEqual({f["code"] for f in data["findings"]}, {"missing", "extra"})

    def test_example_only_needs_no_env(self):
        x = self.write(".env.example", "A=\nB=changeme\n")
        missing_env = os.path.join(self.tmp.name, "nope")
        code, out, _ = self.run_cli("--example-only", "--env", missing_env, "--example", x)
        self.assertEqual(code, 0)
        self.assertIn("0 error(s), 0 warning(s)", out)

    def test_example_only_flags_secret_and_malformed(self):
        x = self.write(".env.example", f"A={SECRET}\nBAD\n")
        code, out, _ = self.run_cli("--example-only", "--example", x, "--strict")
        self.assertEqual(code, 1)
        self.assertIn("malformed", out)
        self.assertIn("example-secret", out)
        self.assertNotIn(SECRET, out)

    def test_values_never_printed(self):
        e = self.write(".env", f"A={SECRET}\nA={SECRET}\nX={SECRET}\nBAD {SECRET}\n")
        x = self.write(".env.example", f"A={SECRET}\nB=need\n")
        for fmt in ("text", "json"):
            _, out, err = self.run_cli("--env", e, "--example", x, "--format", fmt)
            self.assertNotIn(SECRET, out + err)


if __name__ == "__main__":
    unittest.main()

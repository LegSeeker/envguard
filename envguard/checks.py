from __future__ import annotations

import re
from typing import List

from envguard.parser import Finding, ParseResult

_TOKENISH = re.compile(r"^[A-Za-z0-9+/=_\-]+$")
_SECRET_PREFIXES = ("sk_live_", "ghp_", "AKIA")


def looks_like_secret(value: str) -> bool:
    if value.startswith(_SECRET_PREFIXES):
        return True
    return (len(value) >= 20 and bool(_TOKENISH.match(value))
            and any(c.isalpha() for c in value)
            and any(c.isdigit() for c in value))


def _sort_key(f: Finding):
    return (0 if f.severity == "error" else 1, f.line or 0, f.key or "")


def run_checks(env: ParseResult, example: ParseResult) -> List[Finding]:
    findings: List[Finding] = []
    for f in env.issues:
        findings.append(f)
    for f in example.issues:
        findings.append(Finding(f.code, f.key, f.line,
                                f"(in example) {f.message}", f.severity))

    for key, ex_value in example.values.items():
        if key not in env.values:
            findings.append(Finding("missing", key, None,
                                    "required by example but not set", "error"))
        elif env.values[key] == "" and ex_value != "":
            findings.append(Finding("empty", key, env.lines[key],
                                    "set but empty", "error"))
        if looks_like_secret(ex_value):
            findings.append(Finding("example-secret", key, example.lines[key],
                                    "example value looks like a real secret",
                                    "warning"))

    for key in env.values:
        if key not in example.values:
            findings.append(Finding("extra", key, env.lines[key],
                                    "not declared in example", "warning"))

    return sorted(findings, key=_sort_key)

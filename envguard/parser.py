from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ESCAPES = {"n": "\n", '"': '"', "\\": "\\"}


@dataclass
class Finding:
    code: str
    key: Optional[str]
    line: Optional[int]
    message: str
    severity: str

    def to_dict(self) -> dict:
        return {"code": self.code, "key": self.key, "line": self.line,
                "message": self.message, "severity": self.severity}


@dataclass
class ParseResult:
    values: Dict[str, str] = field(default_factory=dict)
    lines: Dict[str, int] = field(default_factory=dict)
    issues: List[Finding] = field(default_factory=list)


def _unescape_double(body: str) -> str:
    out = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body) and body[i + 1] in _ESCAPES:
            out.append(_ESCAPES[body[i + 1]])
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _parse_value(raw: str) -> Optional[str]:
    """Return the decoded value, or None if quoting is unterminated."""
    raw = raw.strip()
    if raw.startswith("'"):
        end = raw.find("'", 1)
        return None if end == -1 else raw[1:end]
    if raw.startswith('"'):
        i = 1
        while i < len(raw):
            if raw[i] == "\\":
                i += 2
                continue
            if raw[i] == '"':
                return _unescape_double(raw[1:i])
            i += 1
        return None
    # Unquoted: an inline comment starts at whitespace followed by '#'.
    m = re.search(r"\s#", raw)
    if m:
        raw = raw[:m.start()]
    return raw.strip()


def parse_env(text: str) -> ParseResult:
    result = ParseResult()
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export "):].lstrip()
        if "=" not in stripped:
            result.issues.append(Finding("malformed", None, lineno,
                                         "line is not KEY=VALUE", "error"))
            continue
        key, raw = stripped.split("=", 1)
        key = key.strip()
        if not KEY_RE.match(key):
            result.issues.append(Finding("malformed", None, lineno,
                                         "invalid key name", "error"))
            continue
        value = _parse_value(raw)
        if value is None:
            result.issues.append(Finding("malformed", key, lineno,
                                         "unterminated quoted value", "error"))
            continue
        if key in result.values:
            result.issues.append(Finding(
                "duplicate", key, lineno,
                f"defined again (first at line {result.lines[key]}); last value wins",
                "warning"))
        result.values[key] = value
        result.lines[key] = lineno
    return result

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from envguard import __version__
from envguard.checks import run_checks
from envguard.parser import parse_env


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="envguard",
        description="Validate a .env file against .env.example. Never prints values.")
    p.add_argument("--env", default=".env", help="path to the env file (default: .env)")
    p.add_argument("--example", default=".env.example",
                   help="path to the example/schema file (default: .env.example)")
    p.add_argument("--strict", action="store_true", help="treat warnings as failures")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--version", action="version", version=f"envguard {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    texts = {}
    for label, path in (("env", args.env), ("example", args.example)):
        try:
            texts[label] = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"envguard: cannot read {label} file {path!r}: {exc.strerror}",
                  file=sys.stderr)
            return 2

    findings = run_checks(parse_env(texts["env"]), parse_env(texts["example"]))
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = len(findings) - errors

    if args.format == "json":
        print(json.dumps({"findings": [f.to_dict() for f in findings],
                          "errors": errors, "warnings": warnings}, indent=2))
    else:
        for f in findings:
            where = f" [line {f.line}]" if f.line else ""
            key = f" {f.key}" if f.key else ""
            print(f"{f.severity.upper()} {f.code}{where}{key}: {f.message}")
        print(f"envguard: {errors} error(s), {warnings} warning(s)")

    if errors or (args.strict and warnings):
        return 1
    return 0

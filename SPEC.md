# envguard — specification

A zero-dependency Python 3.9+ command-line tool that validates `.env` files
against a committed `.env.example` (the "schema"). Original work of Sapra AI.

## Package layout

- `envguard/__init__.py` — exposes `__version__ = "0.1.0"`.
- `envguard/parser.py` — `parse_env(text: str) -> ParseResult`.
- `envguard/checks.py` — `run_checks(env: ParseResult, example: ParseResult) -> list[Finding]`.
- `envguard/cli.py` — `main(argv: list[str] | None = None) -> int`.
- `envguard/__main__.py` — `raise SystemExit(main())`.

## Parser rules

- Blank lines and lines starting with `#` (after stripping whitespace) are ignored.
- Optional leading `export ` prefix is allowed.
- `KEY=VALUE`; KEY must match `^[A-Za-z_][A-Za-z0-9_]*$`.
- VALUE may be unquoted (trailing ` #comment` stripped), single-quoted (literal),
  or double-quoted (supports `\n`, `\"`, `\\` escapes). Surrounding whitespace trimmed.
- Lines without `=` or with an invalid key produce a `malformed` issue with line number.
- Duplicate keys produce a `duplicate` issue (the last value wins).
- `ParseResult` is a dataclass: `values: dict[str, str]`, `lines: dict[str, int]`
  (key -> line number of last definition), `issues: list[Finding]`.

## Finding

Dataclass `Finding(code: str, key: str | None, line: int | None, message: str, severity: str)`
where severity is `"error"` or `"warning"`.

## Checks (`run_checks`)

| code | severity | rule |
|---|---|---|
| `missing` | error | key in example but absent from env |
| `extra` | warning | key in env but absent from example |
| `empty` | error | key present in env with empty value, and example value is not empty |
| `malformed` / `duplicate` | error / warning | parser issues from env (and from example) |
| `example-secret` | warning | example value looks like a real secret: length >= 20 and matches `^[A-Za-z0-9+/=_\-]+$` with both letters and digits, OR starts with `sk_live_`, `ghp_`, `AKIA` |

Findings are sorted by (severity error first, line or 0, key).

## CLI

```
python -m envguard [--env PATH] [--example PATH] [--strict] [--format text|json]
```

- Defaults: `--env .env`, `--example .env.example`.
- `--example-only`: skip the env file; report only example parser issues and `example-secret`.
- Missing file -> print error to stderr, exit code 2.
- Exit 1 if any error finding (or any warning when `--strict`), else 0.
- text format: one line per finding `LEVEL code [line N] KEY: message`, then a summary line
  `envguard: X error(s), Y warning(s)`.
- json format: `{"findings": [...], "errors": X, "warnings": Y}`.
- Values must NEVER be printed (they may be secrets).

# envguard

[![CI](https://github.com/LegSeeker/envguard/actions/workflows/ci.yml/badge.svg)](https://github.com/LegSeeker/envguard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Validate a `.env` file against your committed `.env.example` without ever printing secret values.
Zero dependencies, Python 3.9+, free and open source.

```
$ envguard
ERROR missing STRIPE_WEBHOOK_SECRET: required by example but not set
WARNING extra [line 7] OLD_API_URL: not declared in example
envguard: 1 error(s), 1 warning(s)
```

## Install

```
pip install git+https://github.com/LegSeeker/envguard@v0.1.0
```

Or, with no install, run it from a checkout: `python -m envguard`.

## Usage

```
envguard                                  # check .env against .env.example
envguard --env .env.prod --strict         # warnings fail too
envguard --example-only                   # check only .env.example (CI, pre-commit)
envguard --format json                    # machine-readable output
```

| code | severity | meaning |
|---|---|---|
| `missing` | error | key declared in the example but not set |
| `empty` | error | key set to an empty value when the example has a non-empty placeholder |
| `malformed` | error | line is not `KEY=VALUE`, has an invalid key, or an unterminated quote |
| `extra` | warning | key set but not declared in the example |
| `duplicate` | warning | key defined more than once (last wins) |
| `example-secret` | warning | the example file seems to contain a real credential |

Exit codes: `0` ok, `1` errors (or warnings with `--strict`), `2` file not readable.

Parsing supports comments, `export KEY=...`, inline `# comments` on unquoted values,
single quotes (literal) and double quotes (`\n`, `\"`, `\\` escapes).

## GitHub Action

```yaml
- uses: actions/checkout@v4
- uses: LegSeeker/envguard@v0.1.0
  with:
    strict: "true"          # optional
    # env: .env.ci          # optional: also validate a generated env file
```

With no `env` input, the Action checks `.env.example` only, so your real secrets never need to be in CI.

## pre-commit

```yaml
repos:
  - repo: https://github.com/LegSeeker/envguard
    rev: v0.1.0
    hooks:
      - id: envguard
```

The hook runs whenever `.env.example` changes and blocks commits that add a real-looking secret to it.

## Development

```
python -m unittest discover -s tests -v
```

Issues and pull requests are welcome.

Licensed under MIT (see `LICENSE`). For copyright concerns, see `DMCA.md`.
Made by Sapra AI.

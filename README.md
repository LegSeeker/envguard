# envguard

Validate a `.env` file against your committed `.env.example`, without ever printing secret values.
Zero dependencies, Python 3.9+.

```
python -m envguard                       # checks .env against .env.example
python -m envguard --env .env.prod --strict --format json
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
Use it as a pre-commit hook or CI step.

## Tests

```
python -m unittest discover -s tests -v
```

Licensed under MIT (see `LICENSE`). For copyright concerns, see `DMCA.md`.

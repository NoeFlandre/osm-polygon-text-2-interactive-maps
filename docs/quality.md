# Quality checks

## Tests

```bash
uv run pytest
```

The tests use small fixture files. They do not download data.

## Coverage and CRAP score

The CRAP score combines complexity and coverage. A function has a high CRAP score when it is complex and not tested.

```bash
uv run coverage run -m pytest
uv run coverage json -o coverage.json
uv run python scripts/crap.py coverage.json --below 6
```

The check fails if any function has a CRAP score of 6 or more.

## Mutation testing

Mutation testing changes the code in small ways. A good test suite fails for each change.

```bash
uv run mutmut run
uv run mutmut results
```

The report lists the changes that the tests did not catch.

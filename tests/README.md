# Tests

```bash
python3 -m pip install -r requirements_test.txt
scripts/test -n auto
```

`-n auto` runs the tests in parallel, one process per CPU core. Leave it out to run a single test.

`requirements_test.txt` pins the Home Assistant release the tests run against, and needs Python 3.14.

## Adding an API response as a fixture

Files in `tests/fixtures` are public, so they may only hold anonymized data. Never add a response there by hand.

1. Save the raw response in `custom_components/zonneplan_one/tests/`. That directory is gitignored.
2. Add it to `fixture_names.json` in the same directory, with a public name that describes the scenario and doesn't include anyone's name.
3. Run `python3 scripts/anonymize_fixtures.py`.

The script stops on a string field it doesn't know. Decide whether that field is personal, then add it to the matching list in the script. It also renumbers existing ids when a raw file is added, so a new fixture can change other fixtures and the ids used in `test_sensor.py`.

The battery chart response in `common.py` is made up, because no real one was captured.

The price charts were captured on 2026-11-08. `price_chart` in `common.py` moves them by whole days to the frozen test date, which keeps their hours because both dates are in winter time.

A diagnostics download holds the latest response of each endpoint under `last_api_responses`. To use one, keep the download itself out of the raw directory (for example in a `diagnostics/` subdirectory) and save the responses you need from it as separate raw files.

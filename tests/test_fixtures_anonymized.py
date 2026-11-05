"""Guard against committing personal data: every fixture must only hold made-up identifiers."""

import json
import re
from typing import Any

import pytest

from .common import FIXTURE_DIR

FIXTURES = sorted(FIXTURE_DIR.glob("*.json"))
FIXTURE_IDS = [path.name for path in FIXTURES]
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
SYNTHETIC_UUID_PREFIX = "00000000-0000-4000-8000-"
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+")
# Letters are masked to X, digits to a low counter padded with zeros.
MASKED_IDENTIFIER_RE = re.compile(r"[X_\-.]*(0[X_\-.]*)*\d{0,4}[X_\-.]*")
IDENTIFIER_KEYS = {"electricity_meter_identifier", "gas_meter_identifier", "identifier", "serial_number", "sgn_serial_number"}
ROUNDED_KEYS = {"cycle_count", "expected_delivery", "expected_production", "total_power_measured"}
MAX_SIGNIFICANT_DIGITS = 2
FORBIDDEN_KEYS = {"chat", "access_token", "refresh_token", "token"}


def _values_for(data: Any, keys: set[str]) -> list[Any]:
    """Return all values stored under any of `keys`, at any depth."""
    if isinstance(data, dict):
        found = [value for key, value in data.items() if key in keys]
        return found + [item for value in data.values() for item in _values_for(value, keys)]
    if isinstance(data, list):
        return [item for value in data for item in _values_for(value, keys)]
    return []


def test_there_are_fixtures() -> None:
    assert FIXTURES


@pytest.mark.parametrize("path", FIXTURES, ids=FIXTURE_IDS)
def test_uuids_are_synthetic(path: Any) -> None:
    assert [uuid for uuid in UUID_RE.findall(path.read_text()) if not uuid.startswith(SYNTHETIC_UUID_PREFIX)] == []


@pytest.mark.parametrize("path", FIXTURES, ids=FIXTURE_IDS)
def test_emails_are_on_the_reserved_domain(path: Any) -> None:
    assert [email for email in EMAIL_RE.findall(path.read_text()) if not email.endswith("@example.com")] == []


@pytest.mark.parametrize("path", FIXTURES, ids=FIXTURE_IDS)
def test_identifiers_are_masked(path: Any) -> None:
    values = _values_for(json.loads(path.read_text()), IDENTIFIER_KEYS)

    assert [value for value in values if value and not MASKED_IDENTIFIER_RE.fullmatch(value)] == []


@pytest.mark.parametrize("path", FIXTURES, ids=FIXTURE_IDS)
def test_eans_are_masked(path: Any) -> None:
    values = _values_for(json.loads(path.read_text()), {"ean"})

    assert [value for value in values if value and not value.startswith("0000000000")] == []


@pytest.mark.parametrize("path", FIXTURES, ids=FIXTURE_IDS)
def test_addresses_and_names_are_fake(path: Any) -> None:
    data = json.loads(path.read_text())

    assert {address["street"] for address in _values_for(data, {"address"})} <= {"Teststraat"}
    assert set(_values_for(data, {"full_name"})) <= {"Test User"}
    assert set(_values_for(data, {"first_name"})) <= {"Test"}


@pytest.mark.parametrize("path", FIXTURES, ids=FIXTURE_IDS)
def test_household_totals_are_rounded(path: Any) -> None:
    values = _values_for(json.loads(path.read_text()), ROUNDED_KEYS)

    assert [value for value in values if value is not None and len(str(abs(value)).rstrip("0")) > MAX_SIGNIFICANT_DIGITS] == []


@pytest.mark.parametrize("path", FIXTURES, ids=FIXTURE_IDS)
def test_forbidden_keys_are_absent(path: Any) -> None:
    assert _values_for(json.loads(path.read_text()), FORBIDDEN_KEYS) == []

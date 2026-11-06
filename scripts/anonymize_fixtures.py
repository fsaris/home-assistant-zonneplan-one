#!/usr/bin/env python3
"""
Turn raw Zonneplan API responses into anonymized test fixtures.

Raw responses live in the gitignored RAW_DIR, next to a `fixture_names.json` that maps each raw
file to its public fixture name. Unmapped files are refused, so a filename holding someone's name
never ends up in the repository by accident.

String values are handled by allowlist: a string under a key this script does not know stops the
run. When a new response adds a field, decide whether it is personal before adding it to a list.
"""

import argparse
import json
import re
import sys
from math import floor, log10
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "custom_components" / "zonneplan_one" / "tests"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
NAME_MAP = "fixture_names.json"

UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
TIMESTAMP_RE = re.compile(r"^\d{4}-\d\d-\d\d([T ]\d\d:\d\d(:\d\d(\.\d+)?)?(Z|[+-]\d\d:?\d\d)?)?$")
HAND_MASKED_RE = re.compile(r"[xX\d-]+")
PYTHON_LITERAL_RE = re.compile(r'("(?:[^"\\]|\\.)*")|\b(True|False|None)\b')
PYTHON_LITERALS = {"True": "true", "False": "false", "None": "null"}

# Removed entirely: repeats the name and email, and nothing in the integration reads it.
DROPPED_KEYS = {"chat"}

# Masked keeping the value's length and separators, and the same input always gets the same output.
IDENTIFIER_KEYS = {
    "electricity_meter_code",
    "electricity_meter_identifier",
    "gas_meter_code",
    "gas_meter_identifier",
    "identifier",
    "serial_number",
    "sgn_serial_number",
}

SAFE_STRING_KEYS = {
    "battery_state",
    "charge_point_model_name",
    "code",
    "color",
    "contract_type",
    "control_mode",
    "d",
    "date",
    "deposit_type",
    "description",
    "dsmr_version",
    "dynamic_load_balancing_health",
    "ends_at",
    "group_type",
    "host_device_model_name",
    "inverter_firmware_version",
    "inverter_model_name",
    "inverter_state",
    "label",
    "market_segment",
    "measured_at",
    "module_firmware_version",
    "month",
    "name",
    "p",
    "panel_type",
    "power_preset",
    "proposition_reference",
    "scenario",
    "sgn_firmware",
    "slug",
    "source",
    "start_mode",
    "starts_at",
    "state",
    "status",
    "status_message",
    "status_tip",
    "tariff_group",
    "type",
}

# Rounded: these are close to unique per household, so exact values could be matched to data posted elsewhere.
ROUNDED_KEYS = {
    "cycle_count",
    "expected_delivery",
    "expected_production",
    "total_power_measured",
}
ROUNDED_SIGNIFICANT_DIGITS = 2

FAKE_ADDRESS = {
    "id": "1234AB1",
    "zipcode": "1234 AB",
    "street": "Teststraat",
    "number": "1",
    "addition": "",
    "city": "Testdorp",
    "sunrise": "2025-01-01T07:00:00.000000Z",
    "sunset": "2025-01-01T17:00:00.000000Z",
}

# Parts shorter than this ("1", "Den") also occur in unrelated data, so they are not leak-checked.
MIN_LEAK_CHECK_LENGTH = 4
# Short identifiers such as meter model codes can also occur inside prices or measurements.
MIN_IDENTIFIER_LEAK_CHECK_LENGTH = 8


def round_significant(value: float) -> float:
    """Round to ROUNDED_SIGNIFICANT_DIGITS significant digits, keeping integers as integers."""
    if not value:
        return value
    return round(value, ROUNDED_SIGNIFICANT_DIGITS - 1 - floor(log10(abs(value))))


class UnknownFieldError(ValueError):
    """A string value was found under a key that has not been classified."""


class Anonymizer:
    """Replace personal values, giving a value the same replacement in every file."""

    def __init__(self) -> None:
        self._replacements: dict[str, str] = {}
        self._counter = 0
        self.originals: set[str] = set()

    def _next(self) -> int:
        self._counter += 1
        return self._counter

    def _replace(self, kind: str, original: str, make: Any) -> str:
        key = f"{kind}:{original.lower()}"
        if key not in self._replacements:
            self._replacements[key] = make(self._next())
        self.originals.add(original)
        return self._replacements[key]

    def uuid(self, original: str) -> str:
        return self._replace("uuid", original, lambda n: f"00000000-0000-4000-8000-{n:012d}")

    def uuids_in(self, text: str) -> str:
        return UUID_RE.sub(lambda match: self.uuid(match.group()), text)

    def email(self, original: str) -> str:
        return self._replace("email", original, lambda n: f"user{n}@example.com")

    def ean(self, original: str) -> str:
        return self._replace("ean", original, lambda n: f"{n:018d}")

    def identifier(self, original: str) -> str:
        """Mask letters as X and digits as a counter, so the value keeps its shape."""

        def make(n: int) -> str:
            digits = sum(char.isdigit() for char in original)
            counter = iter(str(n).zfill(digits))
            masked = "".join("X" if char.isalpha() else next(counter, "") if char.isdigit() else char for char in original)
            # A value with too few digit positions gets the rest appended, to stay unique.
            return masked + "".join(counter)

        replacement = self._replace("identifier", original, make)
        # Values already masked by hand ("xxxx-xxxx") look like our own output, and hold nothing to leak.
        if len(original) < MIN_IDENTIFIER_LEAK_CHECK_LENGTH or HAND_MASKED_RE.fullmatch(original):
            self.originals.discard(original)
        return replacement

    def person(self, key: str, original: str) -> str:
        self.originals.update(part for part in original.split() if len(part) >= MIN_LEAK_CHECK_LENGTH)
        return {"first_name": "Test", "full_name": "Test User", "initials": "T.U."}[key]

    def address(self, original: dict[str, Any]) -> dict[str, Any]:
        for field in ("id", "zipcode", "street", "city"):
            value = original.get(field) or ""
            self.originals.add(value)
            self.originals.update(part for part in value.split() if part.isalpha())
        unknown = set(original) - set(FAKE_ADDRESS)
        if unknown:
            msg = f"Unknown address fields: {sorted(unknown)}"
            raise UnknownFieldError(msg)
        return dict(FAKE_ADDRESS)

    def walk(self, value: Any, key: str = "", path: str = "") -> Any:
        if isinstance(value, dict):
            if key == "address":
                return self.address(value)
            # Keys can be connection uuids, so they are rewritten too.
            return {self.uuids_in(k): self.walk(v, k, f"{path}.{k}") for k, v in value.items() if k not in DROPPED_KEYS}
        if isinstance(value, list):
            return [self.walk(item, key, path) for item in value]
        if isinstance(value, str):
            return self._string(key, value, path)
        if key in ROUNDED_KEYS and isinstance(value, int | float) and not isinstance(value, bool):
            return round_significant(value)
        return value

    def _string(self, key: str, value: str, path: str) -> str:
        result = value
        if key == "email":
            result = self.email(value)
        elif key == "ean":
            result = self.ean(value)
        elif key in {"first_name", "full_name", "initials"}:
            result = self.person(key, value)
        elif key in IDENTIFIER_KEYS:
            result = self.identifier(value) if value else value
        elif UUID_RE.search(value):
            result = self.uuids_in(value)
        elif key.endswith(("uuid", "_id")):
            # Placeholder someone typed instead of a uuid: still an id, so never pass it through.
            result = self.identifier(value)
        elif key not in SAFE_STRING_KEYS and not TIMESTAMP_RE.match(value):
            msg = f"Unclassified string field {path!r}: add it to the anonymizer"
            raise UnknownFieldError(msg)
        return result


def load_raw(path: Path) -> Any:
    """Parse a raw capture, which may hold request-line comments and Python-style literals."""
    text = "".join(line for line in path.read_text().splitlines(keepends=True) if not line.lstrip().startswith("#"))
    return json.loads(PYTHON_LITERAL_RE.sub(lambda m: m.group(1) or PYTHON_LITERALS[m.group(2)], text))


def find_leaks(outputs: dict[str, str], originals: set[str]) -> list[str]:
    """Return the fixtures that still contain a replaced value, without printing the value."""
    needles = [value.lower() for value in originals if len(value) >= MIN_LEAK_CHECK_LENGTH]
    return sorted(name for name, text in outputs.items() if any(needle in text.lower() for needle in needles))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=FIXTURE_DIR)
    args = parser.parse_args()

    names = json.loads((args.raw_dir / NAME_MAP).read_text())
    raw_files = sorted(path for path in args.raw_dir.glob("*.json") if path.name != NAME_MAP)

    unmapped = [path.name for path in raw_files if path.name not in names]
    if unmapped:
        print(f"Add these files to {NAME_MAP} first: {unmapped}", file=sys.stderr)
        return 1

    anonymizer = Anonymizer()
    outputs = {}
    for path in raw_files:
        data = anonymizer.walk(load_raw(path), path=names[path.name])
        outputs[names[path.name]] = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    leaks = find_leaks(outputs, anonymizer.originals)
    if leaks:
        print(f"Personal values survived in: {leaks}; nothing was written", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, text in outputs.items():
        (args.output_dir / name).write_text(text)
    print(f"Wrote {len(outputs)} fixtures to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

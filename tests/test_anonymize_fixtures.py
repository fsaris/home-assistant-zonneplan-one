"""Tests for the script that anonymizes raw API responses."""

import json
from pathlib import Path

import anonymize_fixtures
import pytest
from anonymize_fixtures import Anonymizer, UnknownFieldError, find_leaks, load_raw

SOME_UUID = "12345678-90ab-4def-8123-4567890abcde"


def test_uuids_are_replaced_in_keys_values_and_consistently() -> None:
    result = Anonymizer().walk({SOME_UUID: {"uuid": SOME_UUID, "other_uuid": SOME_UUID.upper()}})

    ((key, value),) = result.items()
    assert key.startswith("00000000-0000-4000-8000-")
    assert value == {"uuid": key, "other_uuid": key}


def test_uuid_embedded_in_a_string_is_replaced() -> None:
    result = Anonymizer().walk({"label": f"contract {SOME_UUID}"})

    assert SOME_UUID not in result["label"]
    assert result["label"].startswith("contract 00000000-")


def test_identifier_keeps_shape_and_is_shared_between_keys() -> None:
    result = Anonymizer().walk({"serial_number": "AB-C123456789", "identifier": "AB-C123456789"})

    assert result["serial_number"] == result["identifier"]
    assert result["serial_number"] == "XX-X000000001"


def test_different_identifiers_get_different_replacements() -> None:
    result = Anonymizer().walk({"identifier": "serial_nr1", "serial_number": "serial_nr2"})

    assert result["identifier"] != result["serial_number"]


def test_personal_fields_are_replaced() -> None:
    result = Anonymizer().walk({"email": "someone@gmail.test", "first_name": "Some", "full_name": "Some One", "ean": "871234567890123456"})

    assert result["email"].endswith("@example.com")
    assert result["first_name"] == "Test"
    assert result["full_name"] == "Test User"
    assert result["ean"] == "000000000000000002"


def test_address_is_replaced_as_a_whole() -> None:
    result = Anonymizer().walk({"address": {"street": "Echte Straat", "zipcode": "9999 ZZ", "sunrise": "2025-06-01T03:21:00.000000Z"}})

    assert result["address"]["street"] == "Teststraat"
    assert result["address"]["sunrise"] == "2025-01-01T07:00:00.000000Z"


def test_unknown_address_field_is_refused() -> None:
    with pytest.raises(UnknownFieldError):
        Anonymizer().walk({"address": {"street": "Echte Straat", "latitude": "52.1"}})


def test_chat_is_dropped() -> None:
    assert Anonymizer().walk({"chat": {"user": {"name": "Some One"}}, "code": "E004"}) == {"code": "E004"}


def test_unclassified_string_is_refused() -> None:
    with pytest.raises(UnknownFieldError, match=r"fixture\.new_field"):
        Anonymizer().walk({"new_field": "could be anything"}, path="fixture")


def test_placeholder_in_an_id_field_is_not_passed_through() -> None:
    assert Anonymizer().walk({"some_uuid": "not-a-uuid"})["some_uuid"] == "XXX-X-XXXX1"


def test_non_string_values_and_timestamps_are_kept() -> None:
    data = {"value": 12, "enabled": True, "end_date": None, "measured_at": "2025-01-01T00:00:00.000000Z", "new_date": "2025-01-01"}

    assert Anonymizer().walk(data) == data


@pytest.mark.parametrize(
    ("value", "expected"),
    [(13074780, 13000000), (2591, 2600), (138, 140), (450, 450), (7, 7), (0, 0), (None, None)],
)
def test_household_totals_are_rounded(value: int | None, expected: int | None) -> None:
    result = Anonymizer().walk({"total_power_measured": value})["total_power_measured"]

    assert result == expected
    assert type(result) is type(expected)


def test_other_numbers_are_not_rounded() -> None:
    assert Anonymizer().walk({"value": 13074780}) == {"value": 13074780}


def test_load_raw_accepts_comments_and_python_literals(tmp_path: Path) -> None:
    path = tmp_path / "raw.json"
    path.write_text('# GET /api/contracts/secret\n{"a": None, "b": True, "c": "None of True", "d": false}')

    assert load_raw(path) == {"a": None, "b": True, "c": "None of True", "d": False}


def test_find_leaks_reports_only_the_fixture_name() -> None:
    assert find_leaks({"a.json": "contains SECRET value", "b.json": "clean"}, {"secret"}) == ["a.json"]


def _run_main(monkeypatch: pytest.MonkeyPatch, raw_dir: Path, output_dir: Path) -> int:
    monkeypatch.setattr("sys.argv", ["anonymize", "--raw-dir", str(raw_dir), "--output-dir", str(output_dir)])
    return anonymize_fixtures.main()


def test_main_refuses_unmapped_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "fixture_names.json").write_text("{}")
    (tmp_path / "someones_name.json").write_text("{}")
    output = tmp_path / "out"

    assert _run_main(monkeypatch, tmp_path, output) == 1
    assert not output.exists()


def test_main_writes_under_the_public_name(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "fixture_names.json").write_text('{"someones_name.json": "public.json"}')
    (tmp_path / "someones_name.json").write_text(json.dumps({"email": "someone@gmail.test"}))
    output = tmp_path / "out"

    assert _run_main(monkeypatch, tmp_path, output) == 0
    assert [path.name for path in output.iterdir()] == ["public.json"]
    assert "gmail" not in (output / "public.json").read_text()


def test_main_writes_nothing_when_a_value_survives(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "fixture_names.json").write_text('{"raw.json": "public.json"}')
    (tmp_path / "raw.json").write_text(json.dumps({"email": "someone@gmail.test", "label": "mail someone@gmail.test"}))
    output = tmp_path / "out"

    assert _run_main(monkeypatch, tmp_path, output) == 1
    assert not output.exists()

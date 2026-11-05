"""Tests for reading and writing the dotted value paths sensors are described with."""

import logging
from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.zonneplan_one.const import DOMAIN
from custom_components.zonneplan_one.coordinators.zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator


@pytest.fixture
def coordinator(hass: HomeAssistant) -> ZonneplanDataUpdateCoordinator:
    coordinator = ZonneplanDataUpdateCoordinator(hass, logging.getLogger(__name__), name=DOMAIN, config_entry=None)
    coordinator.data = {"a": {"b": 1}, "items": [{"value": "first"}, {"value": "last"}], "none": None}
    return coordinator


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("a.b", 1),
        ("items.0.value", "first"),
        ("items.-1.value", "last"),
        ("none", None),
        ("none.deeper", None),
        ("missing", None),
        ("a.missing", None),
        ("items.2.value", None),
        ("items.-3.value", None),
        ("a.0", None),
    ],
)
def test_get_data_value(coordinator: ZonneplanDataUpdateCoordinator, path: str, expected: Any) -> None:
    assert coordinator.get_data_value(path) == expected


def test_get_data_value_without_data(coordinator: ZonneplanDataUpdateCoordinator) -> None:
    coordinator.data = None

    assert coordinator.get_data_value("a.b") is None


@pytest.mark.parametrize(
    ("path", "read_back"),
    [
        ("a.b", "a.b"),
        ("a.new", "a.new"),
        ("items.0.value", "items.0.value"),
        ("items.-1.value", "items.-1.value"),
    ],
)
def test_set_data_value(coordinator: ZonneplanDataUpdateCoordinator, path: str, read_back: str) -> None:
    coordinator.set_data_value(path, "changed")

    assert coordinator.get_data_value(read_back) == "changed"


@pytest.mark.parametrize("path", ["missing.b", "items.9.value", "none.b.c"])
def test_set_data_value_ignores_paths_that_do_not_exist(coordinator: ZonneplanDataUpdateCoordinator, path: str) -> None:
    coordinator.set_data_value(path, "changed")

    assert coordinator.data == {"a": {"b": 1}, "items": [{"value": "first"}, {"value": "last"}], "none": None}

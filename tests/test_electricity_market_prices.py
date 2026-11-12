"""Unit tests for derived electricity market prices."""

from datetime import datetime

import pytest
from freezegun import freeze_time
from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import is_up
from homeassistant.setup import async_setup_component

from custom_components.zonneplan_one.const import ZONNEPLAN_API_TIME_ZONE
from custom_components.zonneplan_one.electricity_market_prices import (
    VAT_FACTOR,
    ZONNEPLAN_RETURN_MARKUP_EUR,
    apply_return_bonus,
    current_quarter_start,
    epex_price_from_tax_excluded_amount,
    next_quarter_start,
    quarter_price_key,
    return_compensation_base_from_tax_excluded_amount,
    return_price_from_tax_excluded_amount,
    tax_excluded_amount_to_eur_kwh,
)


@pytest.mark.parametrize(
    ("amount", "expected_epex"),
    [
        pytest.param(0, -ZONNEPLAN_RETURN_MARKUP_EUR / VAT_FACTOR, id="zero"),
        pytest.param(12_100_000, (1.21 - ZONNEPLAN_RETURN_MARKUP_EUR) / VAT_FACTOR, id="sample"),
    ],
)
def test_epex_price_from_tax_excluded_amount(amount: int, expected_epex: float) -> None:
    assert epex_price_from_tax_excluded_amount(amount) == pytest.approx(expected_epex)


def test_tax_excluded_amount_scaling() -> None:
    assert tax_excluded_amount_to_eur_kwh(5_000_000) == pytest.approx(0.5)


def test_return_compensation_base_is_epex_plus_two_cents() -> None:
    amount = 12_100_000
    assert return_compensation_base_from_tax_excluded_amount(amount) == pytest.approx(epex_price_from_tax_excluded_amount(amount) + 0.02)


def test_quarter_start_helpers() -> None:
    moment = datetime(2026, 1, 5, 10, 37, 12, tzinfo=ZONNEPLAN_API_TIME_ZONE)
    assert current_quarter_start(moment).strftime("%H:%M") == "10:30"
    assert next_quarter_start(moment).strftime("%H:%M") == "10:45"
    assert quarter_price_key(current_quarter_start(moment)) == "2026-01-05 10:30"


async def test_return_price_applies_bonus_when_sun_is_up(hass: HomeAssistant) -> None:
    await async_setup_component(hass, "sun", {"sun": {}})
    await hass.async_block_till_done()

    summer_noon = datetime(2026, 6, 21, 12, 0, tzinfo=ZONNEPLAN_API_TIME_ZONE)
    amount = 10_000_000
    with freeze_time(summer_noon):
        assert is_up(hass, summer_noon)
        value, bonus_active = return_price_from_tax_excluded_amount(amount, hass, current_quarter_start())
    assert bonus_active is True
    base = return_compensation_base_from_tax_excluded_amount(amount)
    assert value == pytest.approx(base * 1.1)


async def test_return_price_skips_bonus_when_sun_is_down(hass: HomeAssistant) -> None:
    await async_setup_component(hass, "sun", {"sun": {}})
    await hass.async_block_till_done()

    winter_evening = datetime(2026, 12, 22, 19, 0, tzinfo=ZONNEPLAN_API_TIME_ZONE)
    with freeze_time(winter_evening):
        assert not is_up(hass, winter_evening)
        value, bonus_active = apply_return_bonus(1.0, hass, winter_evening)
    assert bonus_active is False
    assert value == pytest.approx(1.0)

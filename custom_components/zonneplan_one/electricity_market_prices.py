"""Derived electricity market and return compensation prices."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import homeassistant.util.dt as dt_util
from homeassistant.helpers.sun import is_up

from .const import ZONNEPLAN_API_TIME_ZONE

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PRICE_AMOUNT_FACTOR = 0.0000001
VAT_FACTOR = 1.21
ZONNEPLAN_RETURN_MARKUP_EUR = 0.02
RETURN_BONUS_FACTOR = 1.1


def current_quarter_start(at: datetime | None = None) -> datetime:
    """Return the start of the quarter-hour containing ``at`` in the Zonneplan time zone."""
    moment = at or dt_util.now(ZONNEPLAN_API_TIME_ZONE)
    moment = moment.replace(tzinfo=ZONNEPLAN_API_TIME_ZONE) if moment.tzinfo is None else moment.astimezone(ZONNEPLAN_API_TIME_ZONE)
    return moment.replace(minute=(moment.minute // 15) * 15, second=0, microsecond=0)


def next_quarter_start(at: datetime | None = None) -> datetime:
    """Return the start of the quarter-hour after ``at``."""
    return current_quarter_start(at) + timedelta(minutes=15)


def quarter_price_key(quarter_start: datetime) -> str:
    """Coordinator lookup key for a quarter start."""
    return quarter_start.strftime("%Y-%m-%d %H:%M")


def tax_excluded_amount_to_eur_kwh(amount: float) -> float:
    """Convert a Zonneplan API price amount to €/kWh."""
    return amount * PRICE_AMOUNT_FACTOR


def epex_price_from_tax_excluded_amount(amount: float) -> float:
    """Derive the EPEX spot price (€/kWh excl. VAT) from the API tax-excluded consumer price."""
    return (tax_excluded_amount_to_eur_kwh(amount) - ZONNEPLAN_RETURN_MARKUP_EUR) / VAT_FACTOR


def return_compensation_base_from_tax_excluded_amount(amount: float) -> float:
    """Feed-in compensation before zonnebonus: EPEX (excl. VAT) + €0.02."""
    return epex_price_from_tax_excluded_amount(amount) + ZONNEPLAN_RETURN_MARKUP_EUR


def apply_return_bonus(base_eur_kwh: float, hass: HomeAssistant, quarter_start: datetime) -> tuple[float, bool]:
    """Apply the Zonneplan zonnebonus when the sun is above the horizon and the base price is positive."""
    bonus_active = base_eur_kwh > 0 and is_up(hass, quarter_start)
    if bonus_active:
        return base_eur_kwh * RETURN_BONUS_FACTOR, True
    return base_eur_kwh, False


def return_price_from_tax_excluded_amount(
    amount: float | None,
    hass: HomeAssistant,
    quarter_start: datetime,
) -> tuple[float | None, bool]:
    """Return compensation (€/kWh) for energy fed back to the grid and whether the bonus applies."""
    if amount is None:
        return None, False
    base = return_compensation_base_from_tax_excluded_amount(amount)
    return apply_return_bonus(base, hass, quarter_start)

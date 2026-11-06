"""Tests for turning hourly measurements into long-term statistics."""

import re
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.zonneplan_one.api import ZonneplanApiError, ZonneplanRateLimitError
from custom_components.zonneplan_one.const import DOMAIN, ZONNEPLAN_API_TIME_ZONE
from custom_components.zonneplan_one.coordinators.statistics import (
    ElectricityStatisticsService,
    GasStatisticsService,
    StatisticChannelState,
)

from .common import API, CONNECTION_UUID, mock_api
from .conftest import NOW

MODULE = "custom_components.zonneplan_one.coordinators.statistics"
DELIVERED = "zonneplan_one:delivered"
PRODUCED = "zonneplan_one:produced"
GAS = "zonneplan_one:gas"
TODAY = NOW.astimezone(ZONNEPLAN_API_TIME_ZONE).replace(hour=0, minute=0, second=0, microsecond=0)
YESTERDAY = TODAY - timedelta(days=1)
EMPTY_DAY = {"measurement_groups": [{"type": "hours", "measurements": []}]}


def _hour(hour: int, day: datetime = YESTERDAY) -> str:
    return (day + timedelta(hours=hour)).isoformat()


def _electricity_entry(hour: int, delivered: float | None = 1000, produced: float | None = 0, day: datetime = YESTERDAY) -> dict[str, Any]:
    return {"date": _hour(hour, day), "values": {"d": delivered, "p": produced}}


def _day(*measurements: dict[str, Any]) -> dict[str, Any]:
    return {"measurement_groups": [{"type": "days", "measurements": []}, {"type": "hours", "measurements": list(measurements)}]}


def _rate_limit(retry_after: int | None = 10) -> ZonneplanRateLimitError:
    return ZonneplanRateLimitError(MagicMock(), (), status=429, retry_after=retry_after)


def _requested_dates(api: MagicMock) -> list[str]:
    return [re.search(r"date=(.*)$", call.args[1]).group(1) for call in api.async_get.call_args_list]


def _channel_states(service: Any, last_time: datetime, *, total_sum: float = 0.0, last_value: float | None = None) -> dict[str, StatisticChannelState]:
    return {
        config.key: StatisticChannelState(config=config, last_time=last_time, total_sum=total_sum, last_state_value=last_value)
        for config in service.channel_configs
    }


def _rows(states: dict[str, StatisticChannelState], key: str) -> list[tuple[float, float]]:
    return [(pytest.approx(row["state"]), pytest.approx(row["sum"])) for row in states[key].pending]


@pytest.fixture
def api() -> MagicMock:
    api = MagicMock()
    api.async_get = AsyncMock(return_value=EMPTY_DAY)
    return api


@pytest.fixture
def electricity(hass: HomeAssistant, api: MagicMock) -> ElectricityStatisticsService:
    return ElectricityStatisticsService(hass, api, "connection", DELIVERED, PRODUCED)


@pytest.fixture
def gas(hass: HomeAssistant, api: MagicMock) -> GasStatisticsService:
    return GasStatisticsService(hass, api, "connection", GAS)


@pytest.fixture
def added_statistics() -> Generator[MagicMock]:
    with patch(f"{MODULE}.async_add_external_statistics") as mock:
        yield mock


@pytest.fixture
def no_wait() -> Generator[MagicMock]:
    """Replace asyncio in the statistics module, so rate limit pauses don't wait."""
    with patch(f"{MODULE}.asyncio", MagicMock(sleep=AsyncMock())) as mock:
        yield mock


@pytest.fixture
def notifications() -> Generator[MagicMock]:
    with patch(f"{MODULE}.persistent_notification") as mock:
        yield mock


def test_measurements_are_summed_and_production_is_negative(electricity: ElectricityStatisticsService) -> None:
    states = _channel_states(electricity, YESTERDAY - timedelta(hours=1))

    electricity._ingest_measurements([_electricity_entry(0, 1000, -500), _electricity_entry(1, 2000, -250)], states)

    assert _rows(states, "delivered") == [(1.0, 1.0), (2.0, 3.0)]
    assert _rows(states, "produced") == [(0.5, 0.5), (0.25, 0.75)]


def test_sum_continues_from_the_existing_total(electricity: ElectricityStatisticsService) -> None:
    states = _channel_states(electricity, YESTERDAY, total_sum=100.0, last_value=1.0)

    electricity._ingest_measurements([_electricity_entry(1)], states)

    assert _rows(states, "delivered") == [(1.0, 101.0)]


def test_correction_of_the_last_hour_only_adds_the_difference(electricity: ElectricityStatisticsService) -> None:
    states = _channel_states(electricity, YESTERDAY, total_sum=100.0, last_value=1.0)

    electricity._ingest_measurements([_electricity_entry(0, delivered=1500)], states)

    assert _rows(states, "delivered") == [(1.5, 100.5)]


def test_hours_before_the_last_statistic_are_ignored(electricity: ElectricityStatisticsService) -> None:
    states = _channel_states(electricity, YESTERDAY + timedelta(hours=5), total_sum=100.0, last_value=1.0)

    electricity._ingest_measurements([_electricity_entry(4)], states)

    assert states["delivered"].pending == []
    assert states["delivered"].total_sum == pytest.approx(100.0)


def test_future_hours_are_ignored(electricity: ElectricityStatisticsService) -> None:
    states = _channel_states(electricity, TODAY)

    electricity._ingest_measurements([_electricity_entry(23, day=TODAY)], states)

    assert states["delivered"].pending == []


def test_entries_going_back_in_time_are_ignored(electricity: ElectricityStatisticsService) -> None:
    states = _channel_states(electricity, YESTERDAY - timedelta(hours=1))

    electricity._ingest_measurements([_electricity_entry(2), _electricity_entry(1)], states)

    assert _rows(states, "delivered") == [(1.0, 1.0)]


@pytest.mark.parametrize("value", [None, "1000"])
def test_values_that_are_not_numbers_are_skipped(electricity: ElectricityStatisticsService, value: Any) -> None:
    states = _channel_states(electricity, YESTERDAY - timedelta(hours=1))

    electricity._ingest_measurements([_electricity_entry(0, delivered=value, produced=-500)], states)

    assert states["delivered"].pending == []
    assert _rows(states, "produced") == [(0.5, 0.5)]


def test_gas_uses_its_own_fields(gas: GasStatisticsService) -> None:
    states = _channel_states(gas, YESTERDAY - timedelta(hours=1))

    gas._ingest_measurements([{"measured_at": _hour(0), "value": 2000}, {"measured_at": _hour(1), "value": None}], states)

    assert _rows(states, "gas") == [(2.0, 2.0)]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="empty"),
        pytest.param({"measurement_groups": []}, id="no_groups"),
        pytest.param({"measurement_groups": [{"type": "days", "measurements": [{}]}]}, id="no_hours"),
        pytest.param({"measurement_groups": [{"type": "hours", "measurements": None}]}, id="hours_without_list"),
    ],
)
def test_payload_without_hours_has_no_measurements(electricity: ElectricityStatisticsService, payload: dict[str, Any]) -> None:
    assert electricity._extract_measurements(payload, "test") == []


def test_flush_adds_statistics_per_channel_with_metadata(electricity: ElectricityStatisticsService, added_statistics: MagicMock) -> None:
    states = _channel_states(electricity, YESTERDAY - timedelta(hours=1))
    electricity._ingest_measurements([_electricity_entry(0, 1000, -500)], states)

    electricity._flush_pending(states)

    metadata = {call.args[1]["statistic_id"]: call.args[1] for call in added_statistics.call_args_list}
    assert set(metadata) == {DELIVERED, PRODUCED}
    assert metadata[DELIVERED]["source"] == DOMAIN
    assert metadata[DELIVERED]["unit_of_measurement"] == "kWh"
    assert metadata[DELIVERED]["has_sum"] is True
    assert states["delivered"].pending == []


def test_flush_without_measurements_adds_nothing(electricity: ElectricityStatisticsService, added_statistics: MagicMock) -> None:
    electricity._flush_pending(_channel_states(electricity, YESTERDAY))

    added_statistics.assert_not_called()


@pytest.mark.usefixtures("added_statistics")
async def test_first_run_backfills_from_the_first_of_the_month(electricity: ElectricityStatisticsService, api: MagicMock) -> None:
    await electricity.process_payload(EMPTY_DAY)

    # The first request is the attempt to refetch yesterday, which has nothing to correct yet.
    assert _requested_dates(api) == ["2025-12-21", *[f"2025-12-{day:02d}" for day in range(1, 22)]]


@pytest.mark.usefixtures("added_statistics")
async def test_empty_days_are_not_fetched_again_on_the_next_run(electricity: ElectricityStatisticsService, api: MagicMock) -> None:
    await electricity.process_payload(EMPTY_DAY)
    api.async_get.reset_mock()

    await electricity.process_payload(EMPTY_DAY)

    assert _requested_dates(api) == ["2025-12-21"]


async def test_rate_limit_during_backfill_resumes_on_the_next_run(
    electricity: ElectricityStatisticsService, api: MagicMock, added_statistics: MagicMock
) -> None:
    limit_on = {"2025-12-03"}

    async def get(_connection: str, path: str, **_: Any) -> dict[str, Any]:
        if path.split("date=")[1] in limit_on:
            raise _rate_limit()
        return EMPTY_DAY

    api.async_get.side_effect = get

    await electricity.process_payload(_day(_electricity_entry(1, day=TODAY)))

    assert _requested_dates(api)[-1] == "2025-12-03"
    added_statistics.assert_not_called()

    api.async_get.reset_mock()
    limit_on.clear()
    await electricity.process_payload(EMPTY_DAY)

    assert _requested_dates(api)[1] == "2025-12-03"


async def test_measurements_of_today_are_processed_after_the_backfill(electricity: ElectricityStatisticsService, added_statistics: MagicMock) -> None:
    await electricity.process_payload(_day(_electricity_entry(1, day=TODAY)))

    rows = {call.args[1]["statistic_id"]: call.args[2] for call in added_statistics.call_args_list}
    assert [row["sum"] for row in rows[DELIVERED]] == [pytest.approx(1.0)]


async def test_yesterday_is_refetched_once_a_day_and_corrects_the_sum(
    electricity: ElectricityStatisticsService, api: MagicMock, added_statistics: MagicMock
) -> None:
    baseline = {"start": YESTERDAY.timestamp(), "sum": 10.0, "state": 1.0}
    api.async_get.return_value = _day(_electricity_entry(0, delivered=1500, produced=-100))

    with patch(f"{MODULE}.statistics_during_period", return_value={DELIVERED: [baseline], PRODUCED: [baseline]}):
        await electricity.process_payload(EMPTY_DAY)
        assert api.async_get.call_count == 1
        assert "date=2025-12-21" in api.async_get.call_args.args[1]
        assert api.async_get.call_args.kwargs["ignore_etag"] is True

        rows = {call.args[1]["statistic_id"]: call.args[2] for call in added_statistics.call_args_list}
        assert [row["sum"] for row in rows[DELIVERED]] == [pytest.approx(10.5)]

        api.async_get.reset_mock()
        with patch.object(electricity, "_load_current_states", AsyncMock(return_value=_channel_states(electricity, TODAY))):
            await electricity.process_payload(EMPTY_DAY)

    api.async_get.assert_not_called()


async def test_yesterday_is_not_refetched_before_the_cutoff(electricity: ElectricityStatisticsService, api: MagicMock, freezer: Any) -> None:
    freezer.move_to(TODAY + timedelta(minutes=10))

    assert await electricity._refetch_and_process_yesterday(EMPTY_DAY) is False
    api.async_get.assert_not_called()


async def test_failed_refetch_of_yesterday_is_not_fatal(electricity: ElectricityStatisticsService, api: MagicMock) -> None:
    api.async_get.side_effect = _rate_limit()

    assert await electricity._refetch_and_process_yesterday(EMPTY_DAY) is False
    assert electricity._refetched_statistics_yesterday is None


@pytest.mark.usefixtures("notifications")
async def test_manual_backfill_starts_a_day_early_and_includes_today(
    electricity: ElectricityStatisticsService, api: MagicMock, added_statistics: MagicMock
) -> None:
    """The day before the start date is fetched on purpose, to make sure all totals are updated correctly."""
    api.async_get.return_value = _day(_electricity_entry(0, day=TODAY - timedelta(days=3)))

    await electricity.async_backfill_from(TODAY - timedelta(days=2))

    assert _requested_dates(api) == ["2025-12-19", "2025-12-20", "2025-12-21", "2025-12-22"]
    assert api.async_get.call_args.kwargs["ignore_etag"] is True
    added_statistics.assert_not_called()


@pytest.mark.usefixtures("notifications")
async def test_manual_backfill_continues_from_the_recorded_sum(electricity: ElectricityStatisticsService, api: MagicMock, added_statistics: MagicMock) -> None:
    start = YESTERDAY

    async def get(_connection: str, path: str, **_: Any) -> dict[str, Any]:
        return _day(_electricity_entry(0)) if path.endswith("date=2025-12-21") else EMPTY_DAY

    api.async_get.side_effect = get
    rows = {DELIVERED: [{"sum": 1.0, "state": 1.0}, {"sum": 42.0, "state": 2.0}]}

    with patch(f"{MODULE}.statistics_during_period", return_value=rows):
        await electricity.async_backfill_from(start)

    added = {call.args[1]["statistic_id"]: call.args[2] for call in added_statistics.call_args_list}
    assert [row["sum"] for row in added[DELIVERED]] == [pytest.approx(43.0)]
    assert [row["sum"] for row in added[PRODUCED]] == [pytest.approx(0.0)]


@pytest.mark.usefixtures("added_statistics")
async def test_manual_backfill_reports_progress(electricity: ElectricityStatisticsService, notifications: MagicMock) -> None:
    await electricity.async_backfill_from(YESTERDAY)

    titles = [call.args[2] for call in notifications.create.call_args_list]
    assert titles[0] == "Statistics backfill started"
    assert titles[-1] == "Statistics backfill complete"
    assert "Fetched 2025-12-21" in [call.args[1] for call in notifications.create.call_args_list]


@pytest.mark.usefixtures("added_statistics", "notifications")
async def test_manual_backfill_waits_and_retries_on_rate_limit(electricity: ElectricityStatisticsService, api: MagicMock, no_wait: MagicMock) -> None:
    api.async_get.side_effect = [_rate_limit(10), _rate_limit(None), EMPTY_DAY, EMPTY_DAY, EMPTY_DAY]

    await electricity.async_backfill_from(YESTERDAY)

    # Retry-After + 20 on the first attempt, the 60 second default doubled on the second.
    assert [call.args[0] for call in no_wait.sleep.call_args_list] == [30, 120]
    first, second, third, *_ = _requested_dates(api)
    assert first == second == third


@pytest.mark.usefixtures("added_statistics", "no_wait")
async def test_manual_backfill_gives_up_after_three_rate_limits(electricity: ElectricityStatisticsService, api: MagicMock, notifications: MagicMock) -> None:
    api.async_get.side_effect = _rate_limit()

    with pytest.raises(ZonneplanRateLimitError):
        await electricity.async_backfill_from(YESTERDAY)

    assert api.async_get.call_count == 3  # noqa: PLR2004
    assert notifications.create.call_args.args[2] == "Statistics backfill failed"


@pytest.mark.usefixtures("added_statistics")
async def test_manual_backfill_fails_on_a_missing_day(electricity: ElectricityStatisticsService, api: MagicMock, notifications: MagicMock) -> None:
    api.async_get.return_value = None

    with pytest.raises(ZonneplanApiError):
        await electricity.async_backfill_from(YESTERDAY)

    assert notifications.create.call_args.args[2] == "Statistics backfill failed"


async def test_service_stores_statistics_in_the_recorder(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: MockConfigEntry,
    connections: dict[str, Any],
) -> None:
    """Run the whole path once: service, API request, statistics service and the real recorder."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        re.compile(rf"{API}/connections/{CONNECTION_UUID}/electricity-delivered/charts/hours\?date=2025-12-21"),
        json={"data": _day(_electricity_entry(1, 1000, -500), _electricity_entry(2, 2000, 0))},
    )
    mock_api(aioclient_mock, connections, NOW)

    await hass.services.async_call(DOMAIN, "fetch_statistics", {"endpoint": "electricity", "start_date": "2025-12-21"}, blocking=True)
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)

    coordinator = setup_integration.runtime_data.coordinators[CONNECTION_UUID].p1_electricity
    stats = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        YESTERDAY.astimezone(UTC),
        None,
        {coordinator.electricity_delivered_id, coordinator.electricity_produced_id},
        "hour",
        None,
        {"sum", "state"},
    )

    # Later rows come from the measurements of today in the default fixture.
    hours = {(YESTERDAY + timedelta(hours=hour)).timestamp() for hour in (1, 2)}

    def sums(statistic_id: str) -> list[float]:
        return [row["sum"] for row in stats[statistic_id] if row["start"] in hours]

    assert sums(coordinator.electricity_delivered_id) == [pytest.approx(1.0), pytest.approx(3.0)]
    assert sums(coordinator.electricity_produced_id) == [pytest.approx(0.5), pytest.approx(0.5)]

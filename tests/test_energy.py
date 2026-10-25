from datetime import UTC, datetime, timedelta
from math import nan

import pytest

from windiq.calculations import PowerCurvePoint, SiteParameters, TurbineParameters
from windiq.energy import (
    HourlyReading,
    annual_window,
    annualize,
    calculate_window,
    parse_energy_parameters,
    validate_window,
)

START = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def site() -> SiteParameters:
    return SiteParameters(100, 100, 0, 0, 0, 0, 0)


@pytest.fixture
def turbine() -> TurbineParameters:
    return TurbineParameters(
        3,
        25,
        3600,
        (
            PowerCurvePoint(3, 0),
            PowerCurvePoint(4, 1000),
            PowerCurvePoint(25, 3600),
        ),
    )


def test_hourly_coverage_and_kmh_conversion(
    site: SiteParameters, turbine: TurbineParameters
) -> None:
    readings = [
        HourlyReading(START, 4, "m/s", {"wind_speed": 4}),
        HourlyReading(START + timedelta(hours=1), 14.4, "km/h", {"wind_speed": 14.4}),
        HourlyReading(START + timedelta(hours=2), None, "m/s", {"wind_speed": None}),
        HourlyReading(START + timedelta(hours=3), None, "m/s", {"wind_speed": "bad"}),
        HourlyReading(
            START + timedelta(hours=1, minutes=30), 4, "m/s", {"wind_speed": 4}
        ),
    ]
    result = calculate_window(
        readings,
        mast_id="mast-1",
        start=START,
        end=START + timedelta(hours=4),
        site=site,
        turbine=turbine,
    )

    assert result.expected_hours == 4
    assert result.observed_hours == 4
    assert result.usable_hours == 2
    assert result.observed_coverage_pct == pytest.approx(100)
    assert result.usable_coverage_pct == pytest.approx(50)
    assert result.excluded_readings.off_hour == 1
    assert result.excluded_readings.missing_speed == 1
    assert result.excluded_readings.nonnumeric_speed == 1
    assert result.gross_energy_mwh == pytest.approx(2)
    assert result.p50_mwh == pytest.approx(2)
    assert result.p90_mwh == pytest.approx(2)


def test_invalid_and_unsupported_readings_are_excluded(
    site: SiteParameters, turbine: TurbineParameters
) -> None:
    readings = [
        HourlyReading(START, 0, "m/s", {"wind_speed": 0}),
        HourlyReading(START + timedelta(hours=1), -1, "m/s", {"wind_speed": -1}),
        HourlyReading(START + timedelta(hours=2), nan, "m/s", None),
        HourlyReading(START + timedelta(hours=3), 4, "knots", {"wind_speed": 4}),
    ]
    result = calculate_window(
        readings,
        mast_id="mast-1",
        start=START,
        end=START + timedelta(hours=4),
        site=site,
        turbine=turbine,
    )
    assert result.usable_hours == 1
    assert result.excluded_readings.invalid_speed == 2
    assert result.excluded_readings.unsupported_unit == 1
    assert result.gross_energy_mwh == 0


def test_empty_window_and_exclusive_end(
    site: SiteParameters, turbine: TurbineParameters
) -> None:
    result = calculate_window(
        [HourlyReading(START + timedelta(hours=1), 4, "m/s", None)],
        mast_id="mast-1",
        start=START,
        end=START + timedelta(hours=1),
        site=site,
        turbine=turbine,
    )
    assert result.expected_hours == 1
    assert result.observed_hours == 0
    assert result.usable_hours == 0
    assert result.p50_mwh == 0


def test_monthly_energy_and_wind_line_preserve_gaps(
    site: SiteParameters, turbine: TurbineParameters
) -> None:
    start = datetime(2026, 1, 31, 22, tzinfo=UTC)
    readings = [
        HourlyReading(start, 4, "m/s", None),
        HourlyReading(start + timedelta(hours=1), None, "m/s", None),
        HourlyReading(start + timedelta(hours=2), 14.4, "km/h", None),
        HourlyReading(start + timedelta(hours=3), 4, "m/s", None),
    ]
    result = calculate_window(
        readings,
        mast_id="mast-1",
        start=start,
        end=start + timedelta(hours=4),
        site=site,
        turbine=turbine,
    )

    assert [point.month for point in result.monthly_energy] == ["2026-01", "2026-02"]
    assert [point.usable_hours for point in result.monthly_energy] == [1, 2]
    assert [point.p50_mwh for point in result.monthly_energy] == pytest.approx([1, 2])
    assert sum(point.p50_mwh for point in result.monthly_energy) == pytest.approx(
        result.p50_mwh
    )
    assert [point.wind_speed_ms for point in result.wind_7d] == pytest.approx(
        [4, None, 4, 4]
    )


def test_wind_line_is_capped_at_last_seven_days(
    site: SiteParameters, turbine: TurbineParameters
) -> None:
    result = calculate_window(
        [],
        mast_id="mast-1",
        start=START,
        end=START + timedelta(days=10),
        site=site,
        turbine=turbine,
    )
    assert len(result.wind_7d) == 168
    assert result.wind_7d[0].timestamp == START + timedelta(days=3)
    assert result.wind_7d[-1].timestamp == START + timedelta(days=10, hours=-1)
    assert all(point.wind_speed_ms is None for point in result.wind_7d)


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        (datetime(2026, 1, 1), START + timedelta(hours=1), "timezone"),
        (START + timedelta(minutes=30), START + timedelta(hours=1), "UTC hours"),
        (START, START, "later"),
        (START, START + timedelta(days=733), "two years"),
    ],
)
def test_window_validation(start: datetime, end: datetime, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_window(start, end)


def test_upstream_parameters_are_validated() -> None:
    mast = {"id": "mast-1", "measurement_height_m": 100}
    site = {
        "mast_id": "mast-1",
        "shear_exponent": 0.2,
        "losses": {"availability": 0.03, "electrical": 0.02, "wake": 0.05},
        "uncertainty": 0.1,
    }
    turbine = {
        "hub_height_m": 140,
        "cut_in_wind_speed_ms": 3,
        "cut_out_wind_speed_ms": 25,
        "rated_power_kw": 3600,
        "power_curve": [
            {"wind_speed_ms": 3, "power_kw": 0},
            {"wind_speed_ms": 25, "power_kw": 3600},
        ],
    }
    mast_id, site_parameters, turbine_parameters = parse_energy_parameters(
        mast, site, turbine
    )
    assert mast_id == "mast-1"
    assert site_parameters.measurement_height_m == 100
    assert turbine_parameters.power_curve[-1].power_kw == 3600
    with pytest.raises(ValueError, match="mast_id"):
        parse_energy_parameters(mast, site | {"mast_id": "other"}, turbine)


def test_annual_window_and_gap_scaling(
    site: SiteParameters, turbine: TurbineParameters
) -> None:
    start, end = annual_window(datetime(2026, 10, 24, 14, tzinfo=UTC))
    assert start == datetime(2025, 10, 24, tzinfo=UTC)
    assert end == datetime(2026, 10, 24, tzinfo=UTC)
    result = calculate_window(
        [HourlyReading(start, 4, "m/s", None)],
        mast_id="mast-1",
        start=start,
        end=start + timedelta(hours=2),
        site=site,
        turbine=turbine,
    )
    annual = annualize(result)
    assert annual.missing_or_unusable_hours == 1
    assert annual.annualization_factor == 2
    assert annual.p50_mwh == 1
    assert annual.annualized_p50_mwh == 2

    leap_start, leap_end = annual_window(datetime(2024, 2, 29, 9, tzinfo=UTC))
    assert leap_start == datetime(2023, 2, 28, tzinfo=UTC)
    assert leap_end == datetime(2024, 2, 29, tzinfo=UTC)


def test_annual_estimate_is_unavailable_without_usable_hours(
    site: SiteParameters, turbine: TurbineParameters
) -> None:
    result = calculate_window(
        [],
        mast_id="mast-1",
        start=START,
        end=START + timedelta(hours=1),
        site=site,
        turbine=turbine,
    )
    annual = annualize(result)
    assert annual.annualization_factor is None
    assert annual.annualized_p50_mwh is None

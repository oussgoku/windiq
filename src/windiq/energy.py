"""Window selection, coverage, and energy from stored hourly measurements."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import isfinite
from typing import Any

from pydantic import BaseModel

from windiq.calculations import (
    PowerCurvePoint,
    SiteParameters,
    TurbineParameters,
    calculate_energy,
)


@dataclass(frozen=True)
class HourlyReading:
    timestamp: datetime
    wind_speed: float | None
    unit: str
    source_payload: dict[str, object] | None


class ExcludedReadings(BaseModel):
    off_hour: int
    missing_speed: int
    nonnumeric_speed: int
    invalid_speed: int
    unsupported_unit: int


class MonthlyEnergy(BaseModel):
    month: str
    usable_hours: int
    gross_energy_mwh: float
    p50_mwh: float
    p90_mwh: float


class HourlyWind(BaseModel):
    timestamp: datetime
    wind_speed_ms: float | None


class EnergyResult(BaseModel):
    mast_id: str
    window_start: datetime
    window_end: datetime
    expected_hours: int
    observed_hours: int
    usable_hours: int
    observed_coverage_pct: float
    usable_coverage_pct: float
    excluded_readings: ExcludedReadings
    gross_energy_mwh: float
    p50_mwh: float
    p90_mwh: float
    monthly_energy: list[MonthlyEnergy]
    wind_7d: list[HourlyWind]


class AnnualEnergyResult(EnergyResult):
    """Rolling-year estimate; missing/invalid hours use the usable-hour mean."""

    missing_or_unusable_hours: int
    annualization_factor: float | None
    annualized_gross_mwh: float | None
    annualized_p50_mwh: float | None
    annualized_p90_mwh: float | None


def annual_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """The last 12 calendar months ending at the current UTC midnight."""
    if now is not None and now.utcoffset() is None:
        raise ValueError("now must include a timezone")
    end = (
        (now or datetime.now(UTC))
        .astimezone(UTC)
        .replace(hour=0, minute=0, second=0, microsecond=0)
    )
    try:
        start = end.replace(year=end.year - 1)
    except ValueError:  # February 29 has no counterpart in a non-leap year.
        start = end.replace(year=end.year - 1, day=28)
    return start, end


def annualize(result: EnergyResult) -> AnnualEnergyResult:
    """Scale observed energy by coverage; return no estimate with zero usable hours."""
    factor = (
        result.expected_hours / result.usable_hours if result.usable_hours else None
    )
    return AnnualEnergyResult(
        **result.model_dump(),
        missing_or_unusable_hours=result.expected_hours - result.usable_hours,
        annualization_factor=factor,
        annualized_gross_mwh=result.gross_energy_mwh * factor if factor else None,
        annualized_p50_mwh=result.p50_mwh * factor if factor else None,
        annualized_p90_mwh=result.p90_mwh * factor if factor else None,
    )


def parse_energy_parameters(
    mast: dict[str, Any], site: dict[str, Any], turbine: dict[str, Any]
) -> tuple[str, SiteParameters, TurbineParameters]:
    """Build validated calculation inputs from the three upstream resources."""
    mast_id = mast.get("id")
    if not isinstance(mast_id, str) or not mast_id:
        raise ValueError("mast resource needs an id")
    if site.get("mast_id") != mast_id:
        raise ValueError("site mast_id does not match mast resource")
    try:
        losses = site["losses"]
        curve = turbine["power_curve"]
        site_parameters = SiteParameters(
            measurement_height_m=mast["measurement_height_m"],
            hub_height_m=turbine["hub_height_m"],
            shear_exponent=site["shear_exponent"],
            availability_loss=losses["availability"],
            electrical_loss=losses["electrical"],
            wake_loss=losses["wake"],
            uncertainty=site["uncertainty"],
        )
        turbine_parameters = TurbineParameters(
            cut_in_wind_speed_ms=turbine["cut_in_wind_speed_ms"],
            cut_out_wind_speed_ms=turbine["cut_out_wind_speed_ms"],
            rated_power_kw=turbine["rated_power_kw"],
            power_curve=tuple(
                PowerCurvePoint(point["wind_speed_ms"], point["power_kw"])
                for point in curve
            ),
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError("invalid upstream energy parameters") from None
    return mast_id, site_parameters, turbine_parameters


def validate_window(start: datetime, end: datetime) -> tuple[datetime, datetime, int]:
    """Require an end-exclusive window on the UTC hourly grid."""
    if start.utcoffset() is None or end.utcoffset() is None:
        raise ValueError("start and end must include timezone offsets")
    start_utc = start.astimezone(UTC)
    end_utc = end.astimezone(UTC)
    for boundary in (start_utc, end_utc):
        if boundary.minute or boundary.second or boundary.microsecond:
            raise ValueError("start and end must align to UTC hours")
    if end_utc <= start_utc:
        raise ValueError("end must be later than start")
    expected_hours = int((end_utc - start_utc).total_seconds() // 3600)
    if expected_hours > 24 * 366 * 2:
        raise ValueError("window must not exceed two years")
    return start_utc, end_utc, expected_hours


def calculate_window(
    readings: list[HourlyReading],
    *,
    mast_id: str,
    start: datetime,
    end: datetime,
    site: SiteParameters,
    turbine: TurbineParameters,
) -> EnergyResult:
    start_utc, end_utc, expected_hours = validate_window(start, end)
    observed_hours = 0
    off_hour = missing_speed = nonnumeric_speed = invalid_speed = unsupported_unit = 0
    usable_speeds_ms: list[float] = []
    monthly_speeds_ms: dict[str, list[float]] = {}
    wind_speeds_by_hour: dict[datetime, float] = {}
    chart_start = max(start_utc, end_utc - timedelta(days=7))

    for reading in readings:
        if reading.timestamp.utcoffset() is None:
            raise ValueError("stored measurement timestamp has no timezone")
        timestamp = reading.timestamp.astimezone(UTC)
        if not start_utc <= timestamp < end_utc:
            continue
        if timestamp.minute or timestamp.second or timestamp.microsecond:
            off_hour += 1
            continue
        observed_hours += 1

        speed = reading.wind_speed
        if speed is None:
            raw_speed = (reading.source_payload or {}).get("wind_speed")
            if raw_speed is None:
                missing_speed += 1
            else:
                nonnumeric_speed += 1
            continue
        if not isfinite(speed) or speed < 0:
            invalid_speed += 1
            continue
        if reading.unit == "m/s":
            speed_ms = speed
        elif reading.unit == "km/h":
            speed_ms = speed / 3.6
        else:
            unsupported_unit += 1
            continue
        usable_speeds_ms.append(speed_ms)
        monthly_speeds_ms.setdefault(timestamp.strftime("%Y-%m"), []).append(speed_ms)
        if timestamp >= chart_start:
            wind_speeds_by_hour[timestamp] = speed_ms

    estimate = calculate_energy(usable_speeds_ms, turbine, site)
    usable_hours = len(usable_speeds_ms)
    monthly_energy: list[MonthlyEnergy] = []
    month_cursor = start_utc.replace(day=1, hour=0)
    while month_cursor < end_utc:
        month = month_cursor.strftime("%Y-%m")
        speeds = monthly_speeds_ms.get(month, [])
        month_estimate = calculate_energy(speeds, turbine, site)
        monthly_energy.append(
            MonthlyEnergy(
                month=month,
                usable_hours=len(speeds),
                gross_energy_mwh=month_estimate.gross_energy_mwh,
                p50_mwh=month_estimate.p50_mwh,
                p90_mwh=month_estimate.p90_mwh,
            )
        )
        month_cursor = (
            month_cursor.replace(year=month_cursor.year + 1, month=1)
            if month_cursor.month == 12
            else month_cursor.replace(month=month_cursor.month + 1)
        )

    wind_7d: list[HourlyWind] = []
    hour_cursor = chart_start
    while hour_cursor < end_utc:
        wind_7d.append(
            HourlyWind(
                timestamp=hour_cursor,
                wind_speed_ms=wind_speeds_by_hour.get(hour_cursor),
            )
        )
        hour_cursor += timedelta(hours=1)

    return EnergyResult(
        mast_id=mast_id,
        window_start=start_utc,
        window_end=end_utc,
        expected_hours=expected_hours,
        observed_hours=observed_hours,
        usable_hours=usable_hours,
        observed_coverage_pct=100 * observed_hours / expected_hours,
        usable_coverage_pct=100 * usable_hours / expected_hours,
        excluded_readings=ExcludedReadings(
            off_hour=off_hour,
            missing_speed=missing_speed,
            nonnumeric_speed=nonnumeric_speed,
            invalid_speed=invalid_speed,
            unsupported_unit=unsupported_unit,
        ),
        gross_energy_mwh=estimate.gross_energy_mwh,
        p50_mwh=estimate.p50_mwh,
        p90_mwh=estimate.p90_mwh,
        monthly_energy=monthly_energy,
        wind_7d=wind_7d,
    )

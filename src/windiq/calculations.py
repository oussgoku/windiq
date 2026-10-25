"""Pure calculations over observed hourly readings; no time periods are filled in."""

from dataclasses import dataclass
from math import isfinite


def _finite(value: float, name: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
    ):
        raise ValueError(f"{name} must be a finite number")


def _nonnegative(value: float, name: str) -> None:
    _finite(value, name)
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


@dataclass(frozen=True)
class PowerCurvePoint:
    wind_speed_ms: float
    power_kw: float

    def __post_init__(self) -> None:
        _nonnegative(self.wind_speed_ms, "curve wind speed")
        _nonnegative(self.power_kw, "curve power")


@dataclass(frozen=True)
class TurbineParameters:
    cut_in_wind_speed_ms: float
    cut_out_wind_speed_ms: float
    rated_power_kw: float
    power_curve: tuple[PowerCurvePoint, ...]

    def __post_init__(self) -> None:
        _nonnegative(self.cut_in_wind_speed_ms, "cut-in speed")
        _nonnegative(self.cut_out_wind_speed_ms, "cut-out speed")
        _nonnegative(self.rated_power_kw, "rated power")
        if self.cut_out_wind_speed_ms <= self.cut_in_wind_speed_ms:
            raise ValueError("cut-out speed must exceed cut-in speed")
        if self.rated_power_kw == 0:
            raise ValueError("rated power must be positive")
        if len(self.power_curve) < 2:
            raise ValueError("power curve needs at least two points")
        if any(
            left.wind_speed_ms >= right.wind_speed_ms
            for left, right in zip(self.power_curve, self.power_curve[1:])
        ):
            raise ValueError("curve speeds must be strictly increasing")
        if (
            self.power_curve[0].wind_speed_ms > self.cut_in_wind_speed_ms
            or self.power_curve[-1].wind_speed_ms < self.cut_out_wind_speed_ms
        ):
            raise ValueError("power curve must cover cut-in through cut-out")


@dataclass(frozen=True)
class SiteParameters:
    measurement_height_m: float
    hub_height_m: float
    shear_exponent: float
    availability_loss: float
    electrical_loss: float
    wake_loss: float
    uncertainty: float

    def __post_init__(self) -> None:
        for name in ("measurement_height_m", "hub_height_m"):
            value = getattr(self, name)
            _finite(value, name)
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        _finite(self.shear_exponent, "shear_exponent")
        for name in ("availability_loss", "electrical_loss", "wake_loss"):
            value = getattr(self, name)
            _finite(value, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        _nonnegative(self.uncertainty, "uncertainty")


@dataclass(frozen=True)
class EnergyEstimate:
    gross_energy_mwh: float
    p50_mwh: float
    p90_mwh: float


def hub_wind_speed(measured_wind_speed_ms: float, site: SiteParameters) -> float:
    _nonnegative(measured_wind_speed_ms, "measured wind speed")
    return (
        measured_wind_speed_ms
        * (site.hub_height_m / site.measurement_height_m) ** site.shear_exponent
    )


def power_at_wind_speed(hub_wind_speed_ms: float, turbine: TurbineParameters) -> float:
    _nonnegative(hub_wind_speed_ms, "hub wind speed")
    if (
        hub_wind_speed_ms < turbine.cut_in_wind_speed_ms
        or hub_wind_speed_ms > turbine.cut_out_wind_speed_ms
    ):
        return 0.0

    for left, right in zip(turbine.power_curve, turbine.power_curve[1:]):
        if left.wind_speed_ms <= hub_wind_speed_ms <= right.wind_speed_ms:
            fraction = (hub_wind_speed_ms - left.wind_speed_ms) / (
                right.wind_speed_ms - left.wind_speed_ms
            )
            return left.power_kw + fraction * (right.power_kw - left.power_kw)
    raise ValueError("power curve does not cover the operating wind speed")


def summarize_hourly_power(
    hourly_power_kw: list[float], site: SiteParameters
) -> EnergyEstimate:
    """Each supplied power reading represents one observed hour."""
    for power_kw in hourly_power_kw:
        _nonnegative(power_kw, "hourly power")
    gross = sum(hourly_power_kw) / 1000
    p50 = (
        gross
        * (1 - site.availability_loss)
        * (1 - site.electrical_loss)
        * (1 - site.wake_loss)
    )
    return EnergyEstimate(gross, p50, p50 * (1 - 1.282 * site.uncertainty))


def calculate_energy(
    hourly_measured_wind_speeds_ms: list[float],
    turbine: TurbineParameters,
    site: SiteParameters,
) -> EnergyEstimate:
    """Estimate energy only for supplied hourly measurements."""
    hourly_power_kw = [
        power_at_wind_speed(hub_wind_speed(speed, site), turbine)
        for speed in hourly_measured_wind_speeds_ms
    ]
    return summarize_hourly_power(hourly_power_kw, site)

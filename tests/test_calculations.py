from math import inf, nan

import pytest

from windiq.calculations import (
    PowerCurvePoint,
    SiteParameters,
    TurbineParameters,
    calculate_energy,
    hub_wind_speed,
    power_at_wind_speed,
    summarize_hourly_power,
)


@pytest.fixture
def site() -> SiteParameters:
    return SiteParameters(
        measurement_height_m=100,
        hub_height_m=140,
        shear_exponent=0.2,
        availability_loss=0.03,
        electrical_loss=0.02,
        wake_loss=0.05,
        uncertainty=0.1,
    )


@pytest.fixture
def turbine() -> TurbineParameters:
    return TurbineParameters(
        cut_in_wind_speed_ms=3,
        cut_out_wind_speed_ms=25,
        rated_power_kw=3600,
        power_curve=(
            PowerCurvePoint(3, 100),
            PowerCurvePoint(5, 300),
            PowerCurvePoint(25, 3600),
        ),
    )


def test_hub_height_adjustment(site: SiteParameters) -> None:
    assert hub_wind_speed(10, site) == pytest.approx(10 * (140 / 100) ** 0.2)
    assert hub_wind_speed(0, site) == 0


def test_linear_interpolation(turbine: TurbineParameters) -> None:
    assert power_at_wind_speed(4, turbine) == pytest.approx(200)


def test_cut_in_and_cut_out_boundaries(turbine: TurbineParameters) -> None:
    assert power_at_wind_speed(2.99, turbine) == 0
    assert power_at_wind_speed(3, turbine) == pytest.approx(100)
    assert power_at_wind_speed(25, turbine) == pytest.approx(3600)
    assert power_at_wind_speed(25.01, turbine) == 0


def test_hourly_energy_conversion(site: SiteParameters) -> None:
    result = summarize_hourly_power([1000, 2000], site)
    assert result.gross_energy_mwh == pytest.approx(3)


def test_p50_and_p90(site: SiteParameters) -> None:
    result = summarize_hourly_power([1000] * 100, site)
    assert result.gross_energy_mwh == pytest.approx(100)
    assert result.p50_mwh == pytest.approx(90.307)
    # 90.307 * (1 - 1.282 * 0.1); the brief's 78.7306426 is a typo.
    assert result.p90_mwh == pytest.approx(78.7296426)


def test_calculation_uses_only_supplied_hours(
    turbine: TurbineParameters, site: SiteParameters
) -> None:
    result = calculate_energy([0, 4 / (1.4**0.2)], turbine, site)
    assert result.gross_energy_mwh == pytest.approx(0.2)


@pytest.mark.parametrize("speed", [-1, nan, inf, -inf, None])
def test_invalid_wind_speeds_rejected(
    speed: float | None, site: SiteParameters, turbine: TurbineParameters
) -> None:
    with pytest.raises(ValueError):
        hub_wind_speed(speed, site)
    with pytest.raises(ValueError):
        power_at_wind_speed(speed, turbine)


@pytest.mark.parametrize("power", [-1, nan, inf])
def test_invalid_hourly_power_rejected(power: float, site: SiteParameters) -> None:
    with pytest.raises(ValueError):
        summarize_hourly_power([power], site)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"measurement_height_m": 0}, "measurement_height_m"),
        ({"hub_height_m": -1}, "hub_height_m"),
        ({"shear_exponent": nan}, "shear_exponent"),
        ({"availability_loss": -0.1}, "availability_loss"),
        ({"electrical_loss": 1.1}, "electrical_loss"),
        ({"wake_loss": inf}, "wake_loss"),
        ({"uncertainty": -0.1}, "uncertainty"),
    ],
)
def test_invalid_site_parameters_rejected(
    site: SiteParameters, changes: dict[str, float], message: str
) -> None:
    values = vars(site) | changes
    with pytest.raises(ValueError, match=message):
        SiteParameters(**values)


@pytest.mark.parametrize(
    "curve",
    [
        (PowerCurvePoint(3, 0), PowerCurvePoint(3, 100), PowerCurvePoint(25, 3600)),
        (PowerCurvePoint(4, 0), PowerCurvePoint(25, 3600)),
        (PowerCurvePoint(3, 0), PowerCurvePoint(24, 3600)),
    ],
)
def test_invalid_curve_rejected(curve: tuple[PowerCurvePoint, ...]) -> None:
    with pytest.raises(ValueError):
        TurbineParameters(3, 25, 3600, curve)


@pytest.mark.parametrize("value", [-1, nan, inf])
def test_invalid_curve_power_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        PowerCurvePoint(3, value)

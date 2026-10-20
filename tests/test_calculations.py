from datetime import date
import pytest

from calculations import (
    ConsumptionRecord,
    PREDICTED_DATA_TYPE,
    calculate_summary,
    fill_missing_daily_records,
)


def rec(d, u, data_type="measured"):
    return ConsumptionRecord(
        household_id="H", billing_period_id="BP",
        date=d, daily_units=u, input_method="manual",
        data_type=data_type, is_complete=True,
    )


def test_before_period():
    s = calculate_summary(
        target_units=100, period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31), today=date(2023, 12, 31),
        records=[],
    )
    assert s.cumulative_including_today == 0
    assert s.elapsed_days_including_today == 0
    assert s.days_remaining_including_today == 31
    assert s.todays_target_pace_allowance == 0


def test_midperiod():
    recs = [rec(date(2024, 1, 1), 10), rec(date(2024, 1, 2), 8)]
    s = calculate_summary(
        target_units=100, period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 10), today=date(2024, 1, 2),
        records=recs,
    )
    assert s.cumulative_before_today == 10
    assert s.units_today == 8
    assert s.cumulative_including_today == 18
    assert s.elapsed_days_including_today == 2
    assert s.days_remaining_including_today == 9
    assert s.remaining_target_units == 82
    # (100 - 10) / 9 = 10.0; minus 8 used = 2.0 remaining
    assert s.todays_target_pace_allowance == pytest.approx(10.0)
    assert s.remaining_allowance_today == pytest.approx(2.0)
    assert s.average_daily_units == pytest.approx(9.0)
    assert s.baseline_projected_final_units == pytest.approx(90.0)


def test_target_exceeded():
    recs = [rec(date(2024, 1, 1), 60), rec(date(2024, 1, 2), 60)]
    s = calculate_summary(
        target_units=100, period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 3), today=date(2024, 1, 2),
        records=recs,
    )
    assert s.cumulative_including_today == 120
    assert s.remaining_target_units == 0
    assert s.excess_units == 20
    assert s.target_exceeded


def test_after_period():
    recs = [rec(date(2024, 1, 1), 10)]
    s = calculate_summary(
        target_units=100, period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31), today=date(2024, 2, 5),
        records=recs,
    )
    assert s.elapsed_days_including_today == 31
    assert s.days_remaining_including_today == 0
    assert s.todays_target_pace_allowance == 0


def test_estimated_excluded():
    recs = [rec(date(2024, 1, 1), 5, "measured"),
            rec(date(2024, 1, 2), 7, "estimated")]
    s = calculate_summary(
        target_units=100, period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 10), today=date(2024, 1, 2),
        records=recs, include_estimated=False,
    )
    assert s.cumulative_including_today == 5
    assert s.measured_cumulative_units == 5


def test_invalid_target():
    with pytest.raises(ValueError):
        calculate_summary(
            target_units=0, period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 2), today=date(2024, 1, 1),
            records=[],
        )


def test_fill_missing_prefers_historical_over_predictor():
    """Once actual readings exist, gaps use historical average — not target predictor."""
    recs = [rec(date(2024, 1, 1), 10), rec(date(2024, 1, 3), 12)]
    filled = fill_missing_daily_records(
        household_id="H",
        billing_period_id="BP",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 5),
        as_of=date(2024, 1, 4),
        records=recs,
        predict_daily=lambda day, cum, elapsed, rem: 99.0,
    )
    assert [r.date for r in filled] == [
        date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4),
    ]
    assert filled[0].data_type == "measured" and filled[0].daily_units == 10
    # After day 1 (10), missing day 2 uses historical avg = 10
    assert filled[1].data_type == PREDICTED_DATA_TYPE and filled[1].daily_units == pytest.approx(10.0)
    assert filled[2].data_type == "measured" and filled[2].daily_units == 12
    # After days 1+3 actual (avg 11), missing day 4 uses 11 — not predictor 99
    assert filled[3].data_type == PREDICTED_DATA_TYPE and filled[3].daily_units == pytest.approx(11.0)

    s = calculate_summary(
        target_units=100,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 5),
        today=date(2024, 1, 4),
        records=filled,
    )
    assert s.cumulative_including_today == pytest.approx(43.0)
    assert s.predicted_cumulative_units == pytest.approx(21.0)
    assert s.measured_cumulative_units == pytest.approx(22.0)


def test_fill_missing_uses_historical_daily_baseline():
    filled = fill_missing_daily_records(
        household_id="H",
        billing_period_id="BP",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 3),
        as_of=date(2024, 1, 2),
        records=[],
        historical_daily=8.5,
        predict_daily=lambda *a: 99.0,
    )
    assert all(r.data_type == PREDICTED_DATA_TYPE for r in filled)
    assert filled[0].daily_units == pytest.approx(8.5)
    assert filled[1].daily_units == pytest.approx(8.5)


def test_fill_missing_falls_back_to_target_predictor_when_no_history():
    filled = fill_missing_daily_records(
        household_id="H",
        billing_period_id="BP",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 3),
        as_of=date(2024, 1, 2),
        records=[],
        historical_daily=None,
        predict_daily=lambda day, cum, elapsed, rem: 7.0,
    )
    assert filled[0].daily_units == pytest.approx(7.0)
    assert filled[1].daily_units == pytest.approx(7.0)
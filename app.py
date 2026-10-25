"""Amplytics prototype UI.

Streamlit UI

Sections
- Register household
- Manage billing period
- Manage appliances
- Record daily consumption
- Dashboard (calculation engine + baseline + optional ML)

All ML output shown here is labelled as an estimate and its metrics come from
the model_metadata.json produced by training. If models are absent, the UI
falls back to calculation engine + baseline only.
"""

import uuid
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

import db
from billing_periods import format_billing_period_label
from alerts import rule_based_alerts, ml_alert
from calculations import ConsumptionRecord, calculate_summary
from config import CLASSIFIER_WARNING_THRESHOLD, FEATURES
from validation import (
    validate_appliance,
    validate_billing_period,
    validate_daily_record,
)
from model_loader import load_models, models_available, predict

st.set_page_config(page_title="Amplytics", page_icon="⚡", layout="wide")


# ---------- init ----------
db.init_db()

if "nav" not in st.session_state:
    st.session_state.nav = "Register household"


def _get_users():
    return db.list_users()


def _current_user_id() -> str | None:
    return st.session_state.get("user_id")


def _records_for(bp_id: str) -> list[ConsumptionRecord]:
    rows = db.list_daily_records(bp_id)
    return [
        ConsumptionRecord(
            household_id=r["user_id"],
            billing_period_id=r["billing_period_id"],
            date=date.fromisoformat(r["date"]),
            daily_units=float(r["daily_units"]),
            input_method=r["input_method"],
            data_type=r["data_type"],
            is_complete=bool(r["is_complete"]),
        )
        for r in rows
    ]


def _months_bounds(today: date) -> tuple[date, date]:
    start = today.replace(day=1)
    if start.month == 12:
        next_month = date(start.year + 1, 1, 1)
    else:
        next_month = date(start.year, start.month + 1, 1)
    return start, next_month - timedelta(days=1)


# ---------- sidebar ----------
with st.sidebar:
    st.markdown("## ⚡ Amplytics")
    users = _get_users()
    if users:
        labels = {f'{u["display_name"]} ({u["user_id"]})': u["user_id"] for u in users}
        current_label = st.selectbox(
            "Current household",
            options=list(labels.keys()),
            index=0,
            key="user_select",
        )
        st.session_state.user_id = labels[current_label]
    else:
        st.info("No households yet. Register one.")

    st.divider()
    st.session_state.nav = st.radio(
        "Navigation",
        [
            "Register household",
            "Billing period",
            "Appliances",
            "Record daily usage",
            "Dashboard",
        ],
        index=0,
        key="nav_radio",
    )

    st.divider()
    st.caption(
        "Measured vs estimated, baseline vs ML, and rule-based vs ML alerts "
        "are kept separate throughout the UI."
    )


# ---------- pages ----------
nav = st.session_state.nav


if nav == "Register household":
    st.title("Register household")
    with st.form("register_form"):
        display = st.text_input("Holder name")
        email = st.text_input("Email (optional)")
        size = st.number_input("Household size", min_value=1, max_value=20, value=3)
        submitted = st.form_submit_button("Create household")
    if submitted:
        if not display.strip():
            st.error("Holder name is required.")
        else:
            uid = "U-" + uuid.uuid4().hex[:8]
            try:
                db.create_user(uid, email or None, display.strip(), int(size))
                st.success(f"Created household {uid}.")
                st.session_state.user_id = uid
                st.rerun()
            except Exception as e:
                st.error(f"Could not create household: {e}")

    st.subheader("Registered households")
    users = _get_users()
    if users:
        st.dataframe(pd.DataFrame(users), use_container_width=True)


elif nav == "Billing period":
    st.title("Billing period")
    uid = _current_user_id()
    if not uid:
        st.warning("Register or select a household first.")
        st.stop()

    tab_new, tab_existing = st.tabs(["Create", "Existing"])

    with tab_new:
        mode = st.radio(
            "Period type", ["Monthly", "Custom date range"], horizontal=True
        )
        today = date.today()
        if mode == "Monthly":
            default_start, default_end = _months_bounds(today)
        else:
            default_start = today
            default_end = today + timedelta(days=29)

        start = st.date_input("Start date", value=default_start, key="bp_start")
        end = st.date_input("End date", value=default_end, key="bp_end")
        target = st.number_input(
            "Target units (kWh)", min_value=1.0, value=200.0, step=1.0
        )

        prior = db.previous_completed_period(uid, start.isoformat())
        prior_units = float(prior["actual_final_units"]) if prior else None
        if prior_units is not None:
            st.caption(f"Previous completed period units: {prior_units:.2f}")

        if st.button("Create billing period"):
            errors = validate_billing_period(start, end, target)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                bp_id = f"{uid}-{start.isoformat()}"
                db.create_billing_period(
                    bp_id, uid, start, end, float(target), prior_units
                )
                st.success(
                    f"Created period {format_billing_period_label(start.isoformat(), end.isoformat())}."
                )
                st.rerun()

    with tab_existing:
        periods = db.list_billing_periods(uid)
        if not periods:
            st.info("No billing periods yet.")
        else:
            df = pd.DataFrame(periods)
            df["period"] = df.apply(
                lambda row: format_billing_period_label(
                    row["period_start_date"], row["period_end_date"]
                ),
                axis=1,
            )
            st.dataframe(
                df[
                    [
                        "period",
                        "period_start_date",
                        "period_end_date",
                        "target_units",
                        "previous_period_units",
                        "actual_final_units",
                    ]
                ].rename(columns={"period": "billing_period"}),
                use_container_width=True,
            )
            period_labels = {
                p["billing_period_id"]: format_billing_period_label(
                    p["period_start_date"], p["period_end_date"]
                )
                for p in periods
            }
            bp_id = st.selectbox(
                "Update target for",
                df["billing_period_id"].tolist(),
                format_func=period_labels.__getitem__,
            )
            new_target = st.number_input(
                "New target units",
                min_value=1.0,
                value=float(
                    df.loc[df["billing_period_id"] == bp_id, "target_units"].iloc[0]
                ),
                step=1.0,
                key="update_target",
            )
            if st.button("Save new target"):
                db.update_billing_target(bp_id, float(new_target))
                st.success("Target updated. Dashboard will recalculate.")
                st.rerun()


elif nav == "Appliances":
    st.title("Appliances")
    uid = _current_user_id()
    if not uid:
        st.warning("Register or select a household first.")
        st.stop()

    st.info(
        "Appliance estimates are informational. They must NOT be added on top of "
        "meter-based daily records for the same usage."
    )

    with st.form("appliance_form"):
        name = st.text_input("Appliance name")
        atype = st.text_input("Appliance type (optional)")
        watts = st.number_input("Rated power (watts)", min_value=1.0, value=100.0)
        qty = st.number_input("Quantity", min_value=1, value=1)
        hours = st.number_input(
            "Operating hours per day (on used days)",
            min_value=0.0,
            max_value=24.0,
            value=4.0,
        )
        days = st.number_input(
            "Days per week used", min_value=0.0, max_value=7.0, value=7.0
        )
        submitted = st.form_submit_button("Add appliance")
    if submitted:
        errors = validate_appliance(name, watts, qty, hours, days)
        if errors:
            for e in errors:
                st.error(e)
        else:
            db.create_appliance(
                uid,
                name.strip(),
                atype or None,
                float(watts),
                int(qty),
                float(hours),
                float(days),
            )
            st.success("Appliance added.")
            st.rerun()

    rows = db.list_appliances(uid)
    if rows:
        st.subheader("Saved appliances")
        df = pd.DataFrame(rows)
        df["estimated_daily_units"] = (
            df["rated_power_watts"]
            * df["quantity"]
            * df["hours_per_day"]
            / 1000.0
            * df["days_per_week"]
            / 7.0
        )
        st.dataframe(
            df[
                [
                    "appliance_id",
                    "appliance_name",
                    "appliance_type",
                    "rated_power_watts",
                    "quantity",
                    "hours_per_day",
                    "days_per_week",
                    "estimated_daily_units",
                ]
            ],
            use_container_width=True,
        )
        to_delete = st.selectbox(
            "Delete appliance",
            df["appliance_id"].tolist(),
            format_func=lambda x: str(x),
        )
        if st.button("Delete selected appliance"):
            db.delete_appliance(int(to_delete))
            st.rerun()


elif nav == "Record daily usage":
    st.title("Record daily usage")
    uid = _current_user_id()
    if not uid:
        st.warning("Register or select a household first.")
        st.stop()

    periods = db.list_billing_periods(uid)
    if not periods:
        st.warning("Create a billing period first.")
        st.stop()

    periods_by_id = {p["billing_period_id"]: p for p in periods}
    period_labels = {
        bp_id: format_billing_period_label(
            period["period_start_date"], period["period_end_date"]
        )
        for bp_id, period in periods_by_id.items()
    }
    bp_id = st.selectbox(
        "Billing period",
        list(periods_by_id),
        format_func=period_labels.__getitem__,
    )
    period = periods_by_id[bp_id]
    p_start = date.fromisoformat(period["period_start_date"])
    p_end = date.fromisoformat(period["period_end_date"])

    with st.form("daily_form"):
        rec_date = st.date_input(
            "Date", value=p_start, min_value=p_start, max_value=p_end
        )
        units = st.number_input("Units (kWh)", min_value=0.0, value=0.0, step=0.1)
        data_type = st.selectbox("Data type", ["measured", "estimated"])
        input_method = st.selectbox("Input method", ["manual", "import"])
        submitted = st.form_submit_button("Save record")

    if submitted:
        errors = validate_daily_record(
            rec_date, float(units), data_type, input_method, p_start, p_end
        )
        if errors:
            for e in errors:
                st.error(e)
        else:
            db.upsert_daily_record(
                uid,
                period["billing_period_id"],
                rec_date.isoformat(),
                float(units),
                input_method,
                data_type,
                True,
            )
            st.success("Record saved. Calculations will update on the dashboard.")
            st.rerun()

    rows = db.list_daily_records(period["billing_period_id"])
    if rows:
        st.subheader("Existing records")
        st.dataframe(
            pd.DataFrame(rows)[
                ["date", "daily_units", "data_type", "input_method", "is_complete"]
            ],
            use_container_width=True,
        )
        del_date = st.selectbox("Delete a record by date", [r["date"] for r in rows])
        if st.button("Delete record"):
            db.delete_daily_record(period["billing_period_id"], del_date)
            st.rerun()


elif nav == "Dashboard":
    st.title("Dashboard")
    uid = _current_user_id()
    if not uid:
        st.warning("Register or select a household first.")
        st.stop()

    periods = db.list_billing_periods(uid)
    if not periods:
        st.warning("Create a billing period first.")
        st.stop()

    periods_by_id = {p["billing_period_id"]: p for p in periods}
    period_labels = {
        bp_id: format_billing_period_label(
            period["period_start_date"], period["period_end_date"]
        )
        for bp_id, period in periods_by_id.items()
    }
    bp_id = st.selectbox(
        "Billing period",
        list(periods_by_id),
        format_func=period_labels.__getitem__,
    )
    period = periods_by_id[bp_id]

    p_start = date.fromisoformat(period["period_start_date"])
    p_end = date.fromisoformat(period["period_end_date"])
    target = float(period["target_units"])

    today = date.today()
    # clamp for calculation display purposes; engine handles out-of-range dates too
    effective_today = min(max(today, p_start), p_end)

    records = _records_for(period["billing_period_id"])
    summary = calculate_summary(
        target_units=target,
        period_start=p_start,
        period_end=p_end,
        today=effective_today,
        records=records,
        include_estimated=True,
    )

    # ---------- core metrics ----------
    st.subheader("Consumption summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cumulative units (kWh)", f"{summary.cumulative_including_today:.2f}")
    c2.metric("Target units", f"{summary.target_units:.2f}")
    c3.metric("Remaining target", f"{summary.remaining_target_units:.2f}")
    c4.metric("Percent of target", f"{summary.percent_target_consumed:.1f}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Elapsed days (incl. today)", summary.elapsed_days_including_today)
    c6.metric("Days remaining (incl. today)", summary.days_remaining_including_today)
    c7.metric("Today's pace allowance", f"{summary.todays_target_pace_allowance:.2f}")
    c8.metric("Remaining allowance today", f"{summary.remaining_allowance_today:.2f}")

    if summary.excess_units > 0:
        st.error(f"Excess over target: {summary.excess_units:.2f} units.")

    st.caption(
        f"Measured: {summary.measured_cumulative_units:.2f} units · "
        f"Estimated: {summary.estimated_cumulative_units:.2f} units · "
        f"Predicted: {summary.predicted_cumulative_units:.2f} units. "
        "Target-pace allowance is a guideline, not a guarantee."
    )

    # ---------- rule-based alerts ----------
    st.subheader("Rule-based alerts")
    alerts = rule_based_alerts(summary)
    if not alerts:
        st.success("No rule-based alerts.")
    for a in alerts:
        if a["level"] == "danger":
            st.error(f"**{a['title']}** — {a['message']}")
        elif a["level"] == "warning":
            st.warning(f"**{a['title']}** — {a['message']}")
        else:
            st.info(f"**{a['title']}** — {a['message']}")

    # ---------- projections ----------
    st.subheader("Projections")
    colA, colB = st.columns(2)

    with colA:
        st.markdown("**Baseline projection**")
        st.write(
            f"Average daily × period days = "
            f"**{summary.baseline_projected_final_units:.2f} units**"
        )
        if summary.baseline_projected_final_units > summary.target_units:
            st.warning("Baseline projection is above your target.")

    with colB:
        st.markdown("**ML prediction (Linear Regression)**")
        if not models_available():
            st.info(
                "Models not trained yet. Run scripts/train_models.py "
                "(uses synthetic data)."
            )
        else:
            reg, clf, meta = load_models()

            prev = period.get("previous_period_units")
            prev = None if prev is None or pd.isna(prev) else float(prev)

            features = {
                "target_units": summary.target_units,
                "period_days": summary.period_days,
                "elapsed_days": summary.elapsed_days_including_today,
                "days_remaining": summary.days_remaining_including_today,
                "cumulative_units": summary.cumulative_including_today,
                "average_daily_units": summary.average_daily_units,
                "previous_period_units": prev,
            }
            ml_final, ml_proba = predict(reg, clf, features)
            st.write(f"Predicted final units: **{ml_final:.2f}**")
            st.caption(
                "Label: ML estimate. Not a confirmed future bill. "
                f"Metadata source: {meta.get('data_source')}, "
                f"trained_at: {meta.get('trained_at')}."
            )

            # classifier section
            st.markdown("**ML target-exceedance risk (Logistic Regression)**")
            a = ml_alert(ml_proba, CLASSIFIER_WARNING_THRESHOLD)
            if a["level"] == "ml_warning":
                st.warning(f"**{a['title']}** — {a['message']}")
            else:
                st.info(f"**{a['title']}** — {a['message']}")

            with st.expander("Training metadata (from saved model)"):
                st.json(meta)

    # ---------- records table ----------
    st.subheader("Daily records")
    if records:
        df = pd.DataFrame(
            [
                {
                    "date": r.date.isoformat(),
                    "daily_units": r.daily_units,
                    "data_type": r.data_type,
                    "input_method": r.input_method,
                    "is_complete": r.is_complete,
                }
                for r in records
            ]
        )
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No daily records for this period yet.")

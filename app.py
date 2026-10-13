import streamlit as st

from langgraph_agent import (
    run_agent,
    run_daily_summary,
)
from tools import (
    get_daily_metrics,
    detect_hourly_volume_anomalies,
)


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="AI Operations Copilot",
    page_icon="✦",
    layout="wide",
)


# ---------------------------------------------------------
# Custom styling
# ---------------------------------------------------------

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1250px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.035);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 18px 20px;
        border-radius: 16px;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        opacity: 0.7;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 600;
    }

    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0;
    }

    .hero-subtitle {
        opacity: 0.65;
        margin-top: 0.3rem;
        margin-bottom: 2rem;
    }

    .section-label {
        font-size: 0.75rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        opacity: 0.55;
        margin-bottom: 0.5rem;
    }

    .anomaly-card {
        padding: 18px 22px;
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 16px;
        margin: 1rem 0 1.5rem 0;
        background: rgba(255,255,255,0.025);
    }

    .status-unconfirmed {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.15);
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.04em;
    }

    div.stButton > button {
        border-radius: 10px;
        font-weight: 600;
        min-height: 44px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.markdown(
    '<div class="hero-title">✦ AI Operations Copilot</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero-subtitle">'
    'AI-powered operational intelligence for service teams'
    '</div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Navigation
# ---------------------------------------------------------

daily_tab, copilot_tab = st.tabs(
    ["Daily Operations Brief", "Ask Copilot"]
)


# =========================================================
# DAILY OPERATIONS BRIEF
# =========================================================

with daily_tab:

    selected_date = st.selectbox(
        "Select operational day",
        [
            "2026-08-25",
            "2026-08-26",
            "2026-08-27",
        ],
    )

    metrics = get_daily_metrics(selected_date)

    st.markdown(
        '<div class="section-label">Daily overview</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Requests",
        metrics["total_requests"],
    )

    col2.metric(
        "Average wait",
        f'{metrics["average_wait_time_minutes"]:.2f} min',
    )

    col3.metric(
        "Abandoned calls",
        metrics["abandoned_calls"],
    )

    col4.metric(
        "Avg. available agents",
        f'{metrics["average_available_agents"]:.1f}',
    )

    anomaly_result = detect_hourly_volume_anomalies(
        selected_date
    )

    anomalies = anomaly_result["anomalies"]

    st.markdown("### Operational signals")

    if anomalies:
        for anomaly in anomalies:
            start = anomaly["start_time"][11:16]
            end = anomaly["end_time"][11:16]

            st.markdown(
                f"""
                <div class="anomaly-card">
                    <strong>⚡ Volume anomaly detected</strong><br>
                    <span style="opacity:0.7">
                        {start}–{end}
                        &nbsp;·&nbsp;
                        {anomaly["request_count"]} requests
                        &nbsp;·&nbsp;
                        {anomaly["ratio_to_daily_hourly_average"]}×
                        daily hourly average
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    else:
        st.success(
            "No significant hourly volume anomalies detected."
        )

    st.divider()

    if st.button(
        "✦ Generate AI Daily Brief",
        type="primary",
        use_container_width=True,
    ):

        with st.spinner(
            "Analyzing operational signals and investigating anomalies..."
        ):
            summary = run_daily_summary(selected_date)

        st.session_state["daily_summary"] = summary
        st.session_state["daily_summary_date"] = selected_date

    summary = st.session_state.get("daily_summary")

    if (
        summary is not None
        and st.session_state.get("daily_summary_date")
        == selected_date
    ):

        st.markdown("## AI Daily Brief")

        st.markdown(
            '<div class="section-label">Key insights</div>',
            unsafe_allow_html=True,
        )

        for insight in summary.key_insights:
            st.markdown(f"• {insight}")

        if summary.investigations:

            investigation = summary.investigations[0]

            st.markdown("### Incident investigation")

            if investigation.confirmed_root_cause:
                st.markdown(
                    f"**Confirmed root cause:** "
                    f"{investigation.confirmed_root_cause}"
                )
            else:
                st.markdown(
                    """
                    <span class="status-unconfirmed">
                    ROOT CAUSE NOT CONFIRMED
                    </span>
                    """,
                    unsafe_allow_html=True,
                )

            if investigation.supported_patterns:
                st.markdown("#### Supported patterns")

                for pattern in investigation.supported_patterns:
                    st.markdown(f"• {pattern}")

            if investigation.hypotheses:
                st.markdown("#### Likely explanations")

                for hypothesis in investigation.hypotheses:
                    st.markdown(f"• {hypothesis}")

        if summary.recommendations:

            st.markdown("### Recommended actions")

            for recommendation in summary.recommendations:
                st.markdown(f"• {recommendation}")

        with st.expander(
            "View full investigation evidence"
        ):
            st.json(summary.model_dump())


# =========================================================
# ASK COPILOT
# =========================================================

with copilot_tab:

    st.markdown("### Ask about your operation")

    st.caption(
        "Investigate workload spikes, service performance, "
        "request patterns and operational bottlenecks."
    )

    question = st.text_area(
        "Question",
        placeholder=(
            "Why was there unusually high workload "
            "between 12:00 and 13:00 on August 25?"
        ),
        height=120,
    )

    if st.button(
        "Investigate",
        key="investigate",
        type="primary",
    ):

        if not question.strip():
            st.warning("Enter a question first.")

        else:
            with st.spinner(
                "Investigating operational data..."
            ):
                run_agent(question)

            st.info(
                "Investigation completed. "
                "Structured UI rendering will be connected next."
            )
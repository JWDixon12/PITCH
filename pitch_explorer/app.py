"""PITCH — soccer prediction explorer.

Run from the repo root:
    streamlit run pitch_explorer/app.py

This is the entry point. Pages live in pitch_explorer/pages/.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from utils import (
    LEAGUE_NAMES,
    available_dates,
    inject_global_css,
    last_updated_text,
    load_backtest_predictions,
    load_picks_history,
)

ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(
    page_title="PITCH — Soccer Predictions",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <div class="hero-title">⚽ PITCH</div>
      <div class="hero-subtitle">Calibrated soccer predictions across the top-5 European leagues, UCL, UEL, and MLS — with daily Kalshi market comparison.</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Quick stats row
# ---------------------------------------------------------------------------
backtest = load_backtest_predictions()
picks = load_picks_history()
dates = available_dates()

n_matches = len(backtest)
n_leagues = len(LEAGUE_NAMES)
n_picks_lifetime = len(picks)
n_dates = len(dates)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Backtest matches</div>
        <div class="stat-value">{n_matches:,}</div>
        <div class="stat-caption">2019-2025, 7 leagues</div></div>""",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Leagues covered</div>
        <div class="stat-value">{n_leagues}</div>
        <div class="stat-caption">EPL · LaLiga · Serie A · Bundesliga · Ligue 1 · UCL · UEL · MLS</div></div>""",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Picks logged</div>
        <div class="stat-value">{n_picks_lifetime:,}</div>
        <div class="stat-caption">vs Kalshi closing</div></div>""",
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Daily slates</div>
        <div class="stat-value">{n_dates}</div>
        <div class="stat-caption">{last_updated_text()}</div></div>""",
        unsafe_allow_html=True,
    )


st.markdown("### Where to start")
st.markdown(
    """
- **⚽ Today's Slate** — every game today with calibrated probabilities, expected scoreline, totals, BTTS, and Kalshi market edges.
- **📊 Calibration** — when the sim says X%, what actually happens? Per-market calibration tables from a 13.7K-match backtest.
- **🎯 Picks Tracker** — every pick we've ever made vs Kalshi, with lifetime ROI and per-market hit rate.
- **🔍 Match Explorer** — pick any team, opponent, and date — get the same prediction we'd have made that day.
- **📈 Backtest** — the headline numbers behind the model.
- **📖 How It Works** — methodology in plain English.
    """
)

st.divider()

if not dates:
    st.warning(
        "No slate data yet. The model auto-refreshes every morning at 3:30 AM CT. "
        "Once a daily run completes, this page will populate."
    )
else:
    st.success(
        f"Latest slate available: **{dates[0]}**. Click **⚽ Today's Slate** "
        f"in the sidebar to see today's matches."
    )

st.caption(
    "PITCH is calibrated against a 13,708-match multi-season backtest with stacking-model predictions. "
    "It's a research project, not betting advice."
)

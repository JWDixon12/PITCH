"""Calibration page — sim X% probability → actually went X-X (Y%)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import (
    inject_global_css,
    load_calibration_btts, load_calibration_ml, load_calibration_total,
)

st.set_page_config(page_title="Calibration · PITCH", page_icon="📊", layout="wide")
inject_global_css()

st.markdown(
    """<div class="hero">
    <div class="hero-title">📊 Calibration</div>
    <div class="hero-subtitle">When the sim says X%, what actually happened? — from a 13.7K-match backtest.</div>
    </div>""",
    unsafe_allow_html=True,
)

ml = load_calibration_ml()
total = load_calibration_total()
btts = load_calibration_btts()

if ml.empty and total.empty and btts.empty:
    st.warning(
        "No calibration tables on disk yet. Once the daily auto-update has run, "
        "they'll appear here."
    )
    st.stop()


def reliability_chart(df: pd.DataFrame, market: str, title: str):
    sub = df[df["market"] == market].copy() if "market" in df.columns else df.copy()
    if sub.empty:
        return None
    sub = sub.sort_values("pct").reset_index(drop=True)
    sub["predicted"] = sub["pct"] / 100.0
    fig = px.scatter(
        sub, x="predicted", y="actual_rate",
        size="n_games", hover_data=["pct", "n_games", "wins", "losses"],
        labels={"predicted": "Predicted probability", "actual_rate": "Actual hit rate"},
        title=title,
    )
    fig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1,
                   line=dict(color="#8B949E", dash="dash"))
    fig.update_layout(template="plotly_dark", height=420,
                       paper_bgcolor="#0E1117", plot_bgcolor="#0E1117")
    return fig


tabs = st.tabs(["Match outcome (H / D / A)", "Total goals (O1.5 / O2.5 / O3.5)", "BTTS yes"])

# -------- Match outcome --------
with tabs[0]:
    if ml.empty:
        st.warning("Match outcome calibration not yet built.")
    else:
        c1, c2, c3 = st.columns(3)
        for col, label, market in [
            (c1, "Home win", "ML_home"),
            (c2, "Draw",      "Draw"),
            (c3, "Away win",  "ML_away"),
        ]:
            with col:
                fig = reliability_chart(ml, market, f"{label}")
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
        st.markdown("##### Per-percent table (every 5th row)")
        for label, market in [("Home win", "ML_home"), ("Draw", "Draw"), ("Away win", "ML_away")]:
            sub = ml[ml["market"] == market].sort_values("pct").reset_index(drop=True)
            if sub.empty:
                continue
            with st.expander(f"{label}  ({len(sub)} buckets)"):
                show = sub.iloc[::5][["pct", "n_games", "wins", "losses",
                                         "actual_rate", "delta"]].copy()
                show["actual_rate"] = (show["actual_rate"] * 100).round(1).astype(str) + "%"
                show["delta"] = (show["delta"] * 100).round(1).astype(str) + "%"
                show.columns = ["Sim %", "Games", "Wins", "Losses", "Actual %", "Delta"]
                st.dataframe(show, use_container_width=True, hide_index=True)

# -------- Totals --------
with tabs[1]:
    if total.empty:
        st.warning("Total goals calibration not yet built.")
    else:
        lines_avail = sorted(total["line"].dropna().unique().tolist()) if "line" in total.columns else []
        if not lines_avail:
            lines_avail = [1.5, 2.5, 3.5]
        cols = st.columns(len(lines_avail))
        for col, line in zip(cols, lines_avail):
            with col:
                fig = reliability_chart(total, f"Over_{line}", f"Over {line}")
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
        for line in lines_avail:
            sub = total[total["market"] == f"Over_{line}"].sort_values("pct").reset_index(drop=True)
            if sub.empty:
                continue
            with st.expander(f"Over {line}  ({len(sub)} buckets)"):
                show = sub.iloc[::5][["pct", "n_games", "wins", "losses",
                                         "actual_rate", "delta"]].copy()
                show["actual_rate"] = (show["actual_rate"] * 100).round(1).astype(str) + "%"
                show["delta"] = (show["delta"] * 100).round(1).astype(str) + "%"
                show.columns = ["Sim %", "Games", "Overs", "Unders", "Actual %", "Delta"]
                st.dataframe(show, use_container_width=True, hide_index=True)

# -------- BTTS --------
with tabs[2]:
    if btts.empty:
        st.warning("BTTS calibration not yet built.")
    else:
        fig = reliability_chart(btts, "BTTS", "Both teams to score (yes)")
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        with st.expander(f"BTTS yes  ({len(btts)} buckets)"):
            show = btts.iloc[::5][["pct", "n_games", "wins", "losses",
                                       "actual_rate", "delta"]].copy()
            show["actual_rate"] = (show["actual_rate"] * 100).round(1).astype(str) + "%"
            show["delta"] = (show["delta"] * 100).round(1).astype(str) + "%"
            show.columns = ["Sim %", "Games", "Yes hits", "No hits", "Actual %", "Delta"]
            st.dataframe(show, use_container_width=True, hide_index=True)

"""Picks Tracker — every pick we've ever made vs Kalshi closing."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import inject_global_css, league_label, load_picks_history

st.set_page_config(page_title="Picks Tracker · PITCH", page_icon="🎯", layout="wide")
inject_global_css()

st.markdown(
    """<div class="hero">
    <div class="hero-title">🎯 Picks Tracker</div>
    <div class="hero-subtitle">Every edge we've taken vs the Kalshi market — graded once results post.</div>
    </div>""",
    unsafe_allow_html=True,
)

picks = load_picks_history()
if picks.empty:
    st.warning(
        "No picks history yet. Once the daily picker has logged its first edges "
        "and the tracker has graded a few, this page will populate."
    )
    st.stop()


# ---------------------------------------------------------------------------
# Normalize
# ---------------------------------------------------------------------------
picks = picks.copy()
picks["pick_date"] = pd.to_datetime(picks["pick_date"]).dt.date
picks["edge_pct"] = picks["edge"] * 100
picks["sim_pct"]  = picks["sim_prob"] * 100
settled = picks[picks["result"].isin(["WIN", "LOSS"])].copy()
pending = picks[picks["result"].isna()].copy()


# ---------------------------------------------------------------------------
# Headline cards
# ---------------------------------------------------------------------------
n_total   = len(picks)
n_settled = len(settled)
n_pending = len(pending)
wins      = int((settled["result"] == "WIN").sum()) if n_settled else 0
losses    = int((settled["result"] == "LOSS").sum()) if n_settled else 0
hit_rate  = wins / n_settled * 100 if n_settled else 0.0
total_pnl = float(settled["pnl_units"].sum()) if n_settled else 0.0
roi       = total_pnl / n_settled * 100 if n_settled else 0.0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Settled record</div>
        <div class="stat-value">{wins}-{losses}</div>
        <div class="stat-caption">{hit_rate:.1f}% hit rate</div></div>""",
        unsafe_allow_html=True,
    )
with c2:
    color = "#3FB950" if total_pnl >= 0 else "#F85149"
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Lifetime P&L</div>
        <div class="stat-value" style="color:{color}">{total_pnl:+.2f}u</div>
        <div class="stat-caption">flat 1u stake</div></div>""",
        unsafe_allow_html=True,
    )
with c3:
    color = "#3FB950" if roi >= 0 else "#F85149"
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">ROI</div>
        <div class="stat-value" style="color:{color}">{roi:+.2f}%</div>
        <div class="stat-caption">on capital staked</div></div>""",
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Pending</div>
        <div class="stat-value">{n_pending}</div>
        <div class="stat-caption">{n_total} picks lifetime</div></div>""",
        unsafe_allow_html=True,
    )

st.divider()


# ---------------------------------------------------------------------------
# By-market breakdown
# ---------------------------------------------------------------------------
st.markdown("### By market")
if n_settled == 0:
    st.info("No graded picks yet — by-market breakdown will appear once results settle.")
else:
    bm = (settled.groupby("market")
                  .agg(n=("result", "size"),
                       wins=("result", lambda s: (s == "WIN").sum()),
                       pnl=("pnl_units", "sum"),
                       avg_edge=("edge", "mean"))
                  .reset_index())
    bm["losses"]   = bm["n"] - bm["wins"]
    bm["hit_pct"]  = (bm["wins"] / bm["n"] * 100).round(1)
    bm["roi_pct"]  = (bm["pnl"] / bm["n"] * 100).round(2)
    bm["avg_edge"] = (bm["avg_edge"] * 100).round(2)
    bm = bm.sort_values("pnl", ascending=False)
    show = bm[["market", "n", "wins", "losses", "hit_pct",
                "avg_edge", "pnl", "roi_pct"]].copy()
    show.columns = ["Market", "N", "Wins", "Losses", "Hit %",
                     "Avg edge %", "P&L (u)", "ROI %"]
    st.dataframe(show, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# By league
# ---------------------------------------------------------------------------
st.markdown("### By league")
if n_settled == 0:
    st.info("No graded picks yet.")
else:
    bl = (settled.groupby("league_code")
                  .agg(n=("result", "size"),
                       wins=("result", lambda s: (s == "WIN").sum()),
                       pnl=("pnl_units", "sum"))
                  .reset_index())
    bl["losses"]  = bl["n"] - bl["wins"]
    bl["hit_pct"] = (bl["wins"] / bl["n"] * 100).round(1)
    bl["roi_pct"] = (bl["pnl"] / bl["n"] * 100).round(2)
    bl["league"]  = bl["league_code"].apply(league_label)
    bl = bl.sort_values("pnl", ascending=False)
    show = bl[["league", "n", "wins", "losses", "hit_pct",
                "pnl", "roi_pct"]].copy()
    show.columns = ["League", "N", "Wins", "Losses", "Hit %", "P&L (u)", "ROI %"]
    st.dataframe(show, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Bankroll chart
# ---------------------------------------------------------------------------
st.markdown("### Bankroll over time")
if n_settled == 0:
    st.info("Bankroll chart will appear once picks start grading.")
else:
    curve = settled.sort_values("pick_date").copy()
    curve["cum_pnl"] = curve["pnl_units"].cumsum()
    curve["pick_date"] = pd.to_datetime(curve["pick_date"])
    fig = px.line(
        curve, x="pick_date", y="cum_pnl",
        labels={"pick_date": "Date", "cum_pnl": "Cumulative P&L (units)"},
    )
    fig.update_traces(line_color="#00C896")
    fig.add_hline(y=0, line_dash="dash", line_color="#8B949E")
    fig.update_layout(template="plotly_dark", height=380,
                       paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
                       margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Recent + pending
# ---------------------------------------------------------------------------
def _format_picks_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["match"]   = df["home"] + " vs " + df["away"]
    df["league"]  = df["league_code"].apply(league_label)
    df["sim %"]   = df["sim_pct"].round(1)
    df["edge %"]  = df["edge_pct"].round(1)
    df["kalshi"]  = df["kalshi_yes_cents"].astype(int).astype(str) + "¢"
    cols = ["pick_date", "league", "match", "market", "sim %",
             "kalshi", "edge %", "result", "pnl_units"]
    df = df[cols].copy()
    df.columns = ["Date", "League", "Match", "Market", "Sim %",
                   "Kalshi", "Edge %", "Result", "P&L"]
    return df


tab_recent, tab_pending, tab_all = st.tabs(
    [f"Recent settled ({n_settled})", f"Pending ({n_pending})", f"All picks ({n_total})"]
)

with tab_recent:
    if n_settled == 0:
        st.info("No graded picks yet.")
    else:
        recent = settled.sort_values("pick_date", ascending=False).head(50)
        st.dataframe(_format_picks_table(recent), use_container_width=True, hide_index=True)

with tab_pending:
    if n_pending == 0:
        st.info("No pending picks — all caught up.")
    else:
        upcoming = pending.sort_values("pick_date", ascending=True)
        st.dataframe(_format_picks_table(upcoming), use_container_width=True, hide_index=True)

with tab_all:
    all_sorted = picks.sort_values("pick_date", ascending=False)
    st.dataframe(_format_picks_table(all_sorted), use_container_width=True, hide_index=True)


st.divider()
st.caption(
    "P&L convention: each pick risks 1u of capital. WIN at YES @ X¢ pays "
    "(100−X)/X units profit; LOSS pays −1u. ROI = total P&L ÷ count of "
    "settled picks. PITCH is research; not betting advice."
)

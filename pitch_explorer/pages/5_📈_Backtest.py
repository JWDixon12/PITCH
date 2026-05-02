"""Backtest — headline numbers behind the model across 13.7K matches."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import (
    inject_global_css, league_label,
    load_backtest_predictions, load_backtest_summary,
)

st.set_page_config(page_title="Backtest · PITCH", page_icon="📈", layout="wide")
inject_global_css()

st.markdown(
    """<div class="hero">
    <div class="hero-title">📈 Backtest</div>
    <div class="hero-subtitle">Walk-forward, out-of-sample. Each match predicted using only data available before kickoff.</div>
    </div>""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Parse unified_summary.txt into a tidy dataframe
# ---------------------------------------------------------------------------
SECTION_RX = re.compile(r"^---\s*(.*?)\s*\(n=([\d,]+)\)\s*---$")
ROW_RX     = re.compile(r"^\s+(.+?)\s{2,}(\S+)\s+(\S+)\s+(\S+)\s*$")


def _parse_summary(text: str) -> pd.DataFrame:
    rows = []
    section = None
    section_n = None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = SECTION_RX.match(line)
        if m:
            section = m.group(1).strip()
            section_n = int(m.group(2).replace(",", ""))
            continue
        if section is None:
            continue
        if line.lstrip().startswith("model"):
            continue
        m2 = ROW_RX.match(line)
        if not m2:
            continue
        model, n, brier, logloss = m2.groups()
        rows.append({
            "section":  section,
            "section_n": section_n,
            "model":    model.strip(),
            "n":        None if n == "-"       else int(n),
            "brier":    None if brier == "-"   else float(brier),
            "logloss":  None if logloss == "-" else float(logloss),
        })
    return pd.DataFrame(rows)


summary_text = load_backtest_summary()
if not summary_text:
    st.warning("No backtest summary on disk yet.")
    st.stop()

summary_df = _parse_summary(summary_text)


# ---------------------------------------------------------------------------
# Headline numbers
# ---------------------------------------------------------------------------
all_matches = summary_df[summary_df["section"] == "ALL MATCHES"]
top5        = summary_df[summary_df["section"] == "TOP-5 LEAGUES"]
cross       = summary_df[summary_df["section"] == "UCL + UEL (cross-league test)"]

n_total = int(all_matches["section_n"].iloc[0]) if not all_matches.empty else 0

if not all_matches.empty:
    best = all_matches.dropna(subset=["brier"]).sort_values("brier").iloc[0]
    best_model_name = best["model"]
    best_brier      = best["brier"]
else:
    best_model_name = "—"
    best_brier      = float("nan")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Backtest matches</div>
        <div class="stat-value">{n_total:,}</div>
        <div class="stat-caption">2019-06 → 2025-05</div></div>""",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Best model</div>
        <div class="stat-value" style="font-size:1.1rem;line-height:1.3rem">
        {best_model_name}</div>
        <div class="stat-caption">Brier {best_brier:.4f}</div></div>""",
        unsafe_allow_html=True,
    )
with c3:
    if not cross.empty:
        cross_best = cross.dropna(subset=["brier"]).sort_values("brier").iloc[0]
        st.markdown(
            f"""<div class="stat-card"><div class="stat-label">Best on UCL+UEL</div>
            <div class="stat-value" style="font-size:1.1rem;line-height:1.3rem">
            {cross_best['model']}</div>
            <div class="stat-caption">Brier {cross_best['brier']:.4f}</div></div>""",
            unsafe_allow_html=True,
        )

st.divider()


# ---------------------------------------------------------------------------
# Section tabs
# ---------------------------------------------------------------------------
PRIMARY = ["ALL MATCHES", "TOP-5 LEAGUES", "UCL + UEL (cross-league test)"]
LEAGUE_SECTIONS = sorted(
    [s for s in summary_df["section"].unique() if s.startswith("League:")]
)


def _render_section(section_name: str, df: pd.DataFrame):
    if df.empty:
        st.info(f"No data for {section_name}.")
        return
    show = df.copy()
    show["n"]       = show["n"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
    show["brier"]   = show["brier"].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
    show["logloss"] = show["logloss"].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "—")
    show = show[["model", "n", "brier", "logloss"]]
    show.columns = ["Model", "N", "Brier ↓", "Log-loss ↓"]
    st.dataframe(show, use_container_width=True, hide_index=True)

    # Bar chart of brier
    plot_df = df.dropna(subset=["brier"]).sort_values("brier")
    if not plot_df.empty:
        fig = px.bar(
            plot_df, x="brier", y="model", orientation="h",
            text=plot_df["brier"].apply(lambda v: f"{v:.4f}"),
            labels={"brier": "Brier (lower is better)", "model": ""},
        )
        fig.update_traces(marker_color="#00C896", textposition="outside")
        fig.update_layout(template="plotly_dark", height=320,
                           paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
                           margin=dict(l=10, r=40, t=10, b=10),
                           yaxis={"categoryorder": "total descending"})
        st.plotly_chart(fig, use_container_width=True)


tab_all, tab_top5, tab_cross, tab_leagues = st.tabs(
    ["All matches", "Top-5 leagues", "UCL + UEL (cross-league)", "Per league"]
)

with tab_all:
    st.markdown(f"##### All matches  (n = {n_total:,})")
    _render_section("ALL MATCHES", all_matches)
    st.caption(
        "The Pinnacle closing line is the toughest possible benchmark — those "
        "are the world's sharpest market makers after every late lineup news. "
        "Beating it on Brier across all matches is essentially impossible. "
        "The goal is to be close, and to beat it on the cross-league subset "
        "(UCL/UEL) where market liquidity is thinner."
    )

with tab_top5:
    st.markdown(f"##### EPL · LaLiga · Serie A · Bundesliga · Ligue 1")
    _render_section("TOP-5 LEAGUES", top5)

with tab_cross:
    st.markdown("##### Champions League + Europa League")
    _render_section("UCL + UEL (cross-league test)", cross)
    st.caption(
        "Cross-league matches are the hardest test: a 13th-place EPL side might "
        "draw a 2nd-place Bundesliga side. Per-league models can't translate. "
        "The global goal-Poisson with league offsets explicitly handles this and "
        "is the best model on this subset."
    )

with tab_leagues:
    if not LEAGUE_SECTIONS:
        st.info("No per-league sections in the summary.")
    else:
        league_pick = st.selectbox(
            "League",
            LEAGUE_SECTIONS,
            format_func=lambda s: s.replace("League: ", ""),
        )
        sub = summary_df[summary_df["section"] == league_pick]
        n_league = int(sub["section_n"].iloc[0]) if not sub.empty else 0
        st.markdown(f"##### {league_pick.replace('League: ', '')}  (n = {n_league:,})")
        _render_section(league_pick, sub)


st.divider()


# ---------------------------------------------------------------------------
# Sample size by league (from predictions parquet)
# ---------------------------------------------------------------------------
bt = load_backtest_predictions()
if not bt.empty:
    st.markdown("### Sample by league × season")
    pivot = (bt.groupby(["league_code", "season"])
                .size().unstack(fill_value=0)
                .rename(index=lambda c: league_label(c)))
    pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("Total", ascending=False)
    st.dataframe(pivot, use_container_width=True)


st.divider()
with st.expander("Raw summary text (verbatim from build)"):
    st.code(summary_text, language="text")

st.caption(
    "Brier score: Σ(p − y)² across H/D/A — perfect = 0, random three-way ≈ 0.667. "
    "Log-loss: −Σ y·log(p) — lower is better. "
    "All numbers are out-of-sample (the predictor never saw the match it's predicting)."
)

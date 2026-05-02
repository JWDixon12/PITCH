"""Match Explorer — pick any team / opponent / date and see what we'd have predicted."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import inject_global_css, league_label, load_backtest_predictions

st.set_page_config(page_title="Match Explorer · PITCH", page_icon="🔍", layout="wide")
inject_global_css()

st.markdown(
    """<div class="hero">
    <div class="hero-title">🔍 Match Explorer</div>
    <div class="hero-subtitle">Browse every prediction we've made across 13.7K backtest matches.</div>
    </div>""",
    unsafe_allow_html=True,
)

bt = load_backtest_predictions()
if bt.empty:
    st.warning("No backtest predictions on disk yet.")
    st.stop()

bt = bt.copy()
bt["match_date"] = pd.to_datetime(bt["match_date"])
bt["date_only"]  = bt["match_date"].dt.date


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.markdown("### Filters")

leagues = sorted(bt["league_code"].unique().tolist())
sel_leagues = st.sidebar.multiselect(
    "Leagues", leagues, default=leagues, format_func=league_label,
)
df = bt[bt["league_code"].isin(sel_leagues)] if sel_leagues else bt

teams = sorted(set(df["home"].unique()).union(df["away"].unique()))
team = st.sidebar.selectbox("Team", ["(any)"] + teams)
opponent = st.sidebar.selectbox("Opponent", ["(any)"] + teams)

seasons = sorted(df["season"].unique().tolist())
sel_seasons = st.sidebar.multiselect("Seasons", seasons, default=seasons)
if sel_seasons:
    df = df[df["season"].isin(sel_seasons)]

results_avail = sorted(df["ftr"].dropna().unique().tolist())
sel_results = st.sidebar.multiselect(
    "Result (FTR)", results_avail, default=results_avail,
    help="H = home win, D = draw, A = away win",
)
if sel_results:
    df = df[df["ftr"].isin(sel_results)]


# ---------------------------------------------------------------------------
# Filter by team / opponent
# ---------------------------------------------------------------------------
if team != "(any)":
    df = df[(df["home"] == team) | (df["away"] == team)]
if opponent != "(any)":
    df = df[(df["home"] == opponent) | (df["away"] == opponent)]

st.caption(f"{len(df):,} matches match these filters")

if df.empty:
    st.info("No matches match the current filters. Loosen them on the left.")
    st.stop()


# ---------------------------------------------------------------------------
# Summary across selection
# ---------------------------------------------------------------------------
st.markdown("### Summary across selection")

def _win_rate(sub: pd.DataFrame, col_h: str, col_a: str) -> tuple[float, float, float]:
    """Return mean predicted (home, draw, away) probability across rows."""
    return (
        sub[col_h].dropna().mean(),
        sub[col_a.replace("p_a", "p_d") if "p_a" in col_a else col_a].dropna().mean(),
        sub[col_a].dropna().mean(),
    )

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Matches</div>
        <div class="stat-value">{len(df):,}</div>
        <div class="stat-caption">in current selection</div></div>""",
        unsafe_allow_html=True,
    )
with c2:
    n_h = int((df["ftr"] == "H").sum())
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Home wins</div>
        <div class="stat-value">{n_h/len(df)*100:.1f}%</div>
        <div class="stat-caption">{n_h} / {len(df)}</div></div>""",
        unsafe_allow_html=True,
    )
with c3:
    n_d = int((df["ftr"] == "D").sum())
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Draws</div>
        <div class="stat-value">{n_d/len(df)*100:.1f}%</div>
        <div class="stat-caption">{n_d} / {len(df)}</div></div>""",
        unsafe_allow_html=True,
    )
with c4:
    n_a = int((df["ftr"] == "A").sum())
    st.markdown(
        f"""<div class="stat-card"><div class="stat-label">Away wins</div>
        <div class="stat-value">{n_a/len(df)*100:.1f}%</div>
        <div class="stat-caption">{n_a} / {len(df)}</div></div>""",
        unsafe_allow_html=True,
    )

st.divider()


# ---------------------------------------------------------------------------
# Match table
# ---------------------------------------------------------------------------
st.markdown("### Per-match predictions")

MODELS = {
    "Stacking (final)":  ("stack_p_h", "stack_p_d", "stack_p_a"),
    "Ensemble":          ("ens_p_h",   "ens_p_d",   "ens_p_a"),
    "Global goal-Poisson": ("global_p_h", "global_p_d", "global_p_a"),
    "Per-league Poisson":  ("per_lg_p_h", "per_lg_p_d", "per_lg_p_a"),
    "API-Football":      ("api_pred_h", "api_pred_d", "api_pred_a"),
    "Market-implied":    ("market_p_h", "market_p_d", "market_p_a"),
}

model_choice = st.selectbox("Show probabilities from", list(MODELS.keys()))
ph, pd_col, pa = MODELS[model_choice]

show = df.sort_values("match_date", ascending=False).copy()
show["league"] = show["league_code"].apply(league_label)
show["date"]   = show["match_date"].dt.strftime("%Y-%m-%d")
show["match"]  = show["home"] + " vs " + show["away"]
show["pH"]     = (show[ph]    * 100).round(1)
show["pD"]     = (show[pd_col]* 100).round(1)
show["pA"]     = (show[pa]    * 100).round(1)
show["FTR"]    = show["ftr"]

# Highlight when prediction was right (highest of pH/pD/pA matches FTR)
def _hit(row):
    if pd.isna(row["pH"]) or pd.isna(row["FTR"]):
        return ""
    probs = {"H": row["pH"], "D": row["pD"], "A": row["pA"]}
    pred = max(probs, key=probs.get)
    return "✓" if pred == row["FTR"] else "✗"

show["right?"] = show.apply(_hit, axis=1)

cols = ["date", "league", "match", "pH", "pD", "pA", "FTR", "right?"]
show_table = show[cols].copy()
show_table.columns = ["Date", "League", "Match", "Home %", "Draw %",
                       "Away %", "FTR", "Hit"]

st.dataframe(show_table.head(500), use_container_width=True, hide_index=True)
if len(show_table) > 500:
    st.caption(f"Showing 500 of {len(show_table):,} matches — narrow filters to see more.")


# ---------------------------------------------------------------------------
# Hit rate of the selected model on this selection
# ---------------------------------------------------------------------------
st.divider()
st.markdown(f"### {model_choice} accuracy on this selection")

valid = df.dropna(subset=[ph, pd_col, pa, "ftr"]).copy()
if valid.empty:
    st.info("No predictions available for this model on the current selection.")
else:
    pred_col = valid[[ph, pd_col, pa]].idxmax(axis=1)
    pred_letter = pred_col.map({ph: "H", pd_col: "D", pa: "A"})
    hits = (pred_letter == valid["ftr"]).sum()
    n    = len(valid)

    def _brier(row):
        actual = {"H": [1, 0, 0], "D": [0, 1, 0], "A": [0, 0, 1]}.get(row["ftr"])
        if actual is None:
            return np.nan
        p = [row[ph], row[pd_col], row[pa]]
        return sum((pi - ai) ** 2 for pi, ai in zip(p, actual))

    brier = valid.apply(_brier, axis=1).dropna().mean()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""<div class="stat-card"><div class="stat-label">Top-1 hit rate</div>
            <div class="stat-value">{hits/n*100:.1f}%</div>
            <div class="stat-caption">{hits} of {n} matches</div></div>""",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""<div class="stat-card"><div class="stat-label">Brier (3-way)</div>
            <div class="stat-value">{brier:.4f}</div>
            <div class="stat-caption">lower is better</div></div>""",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""<div class="stat-card"><div class="stat-label">Sample</div>
            <div class="stat-value">{n:,}</div>
            <div class="stat-caption">predictions evaluated</div></div>""",
            unsafe_allow_html=True,
        )

st.caption(
    "Predictions shown are the out-of-sample backtest values produced by walk-forward "
    "training (each match was predicted using only data available before its kickoff)."
)

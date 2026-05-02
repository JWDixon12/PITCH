"""Today's Best Picks — every market with positive edge, sorted by Kelly size."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import (
    available_dates, calibrate_lookup, cents_to_american, edge_html,
    inject_global_css, kalshi_implied, league_label,
    load_calibration_btts, load_calibration_ml, load_calibration_total,
    load_kalshi, load_slate, load_today_fixtures, team_abbr, today_ct_date,
)

st.set_page_config(
    page_title="Today's Best Picks · PITCH",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_css()


# ---------------------------------------------------------------------------
# Sticky top toolbar — same pattern as the slate
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
      [data-testid="stMain"],
      [data-testid="stMain"] > div,
      [data-testid="stMain"] .block-container,
      [data-testid="stMain"] [data-testid="stVerticalBlock"] {
          overflow: visible !important;
      }
      [data-testid="stHeader"] {
          background: rgba(14, 17, 23, 0.85) !important;
          backdrop-filter: blur(6px);
          z-index: 99 !important;
      }
      [data-testid="stElementContainer"]:has(.pitch-toolbar-anchor) {
          height: 0 !important;
          margin: 0 !important;
          padding: 0 !important;
          overflow: hidden !important;
      }
      [data-testid="stElementContainer"]:has(.pitch-toolbar-anchor)
        + [data-testid="stHorizontalBlock"] {
          position: sticky !important;
          top: 3rem;
          z-index: 100 !important;
          background: #0E1117;
          padding: 14px 1rem 12px 1rem !important;
          margin: 0 -1rem 1rem -1rem !important;
          border-bottom: 2px solid #1F2933;
          box-shadow: 0 4px 12px rgba(0,0,0,0.4);
      }
      [data-testid="stElementContainer"]:has(.pitch-toolbar-anchor)
        + [data-testid="stHorizontalBlock"] label {
          font-size: 11px !important;
          color: #8B949E !important;
          text-transform: uppercase;
          letter-spacing: 0.06em;
      }
      .block-container { padding-top: 1rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Load + filters
# ---------------------------------------------------------------------------
dates = available_dates()
default = today_ct_date().isoformat()
if default not in dates and dates:
    default = dates[0]
elif not dates:
    dates = [default]

st.markdown('<div class="pitch-toolbar-anchor"></div>', unsafe_allow_html=True)

tb_date, tb_leagues, tb_settings = st.columns([2, 4, 3])
date_str = tb_date.selectbox(
    "Slate date", dates,
    index=dates.index(default) if default in dates else 0,
)

sim       = load_slate(date_str)
kalshi    = load_kalshi(date_str)
fixtures  = load_today_fixtures()
cal_ml    = load_calibration_ml()
cal_total = load_calibration_total()
cal_btts  = load_calibration_btts()

st.markdown(
    """<div class="hero">
    <div class="hero-title">🎯 Today's Best Picks</div>
    <div class="hero-subtitle">Every market with positive edge vs Kalshi, sized by the Kelly criterion.</div>
    </div>""",
    unsafe_allow_html=True,
)

if sim.empty or kalshi.empty:
    tb_leagues.empty()
    tb_settings.empty()
    st.warning(
        f"No picks for {date_str}. Either no slate is loaded yet, or the live "
        "Kalshi markets haven't been pulled. Check back after the next refresh."
    )
    st.stop()

# Merge fixtures (for venue display) and Kalshi
if not fixtures.empty:
    fix_cols = ["fixture_id", "home_api_id", "away_api_id", "venue", "round"]
    have = [c for c in fix_cols if c in fixtures.columns]
    sim = sim.merge(fixtures[have], on="fixture_id", how="left")
sim = sim.merge(kalshi, on="fixture_id", how="left")

leagues_in_slate = sorted(sim["league_code"].dropna().unique().tolist())
selected = tb_leagues.multiselect(
    "Leagues", leagues_in_slate, default=leagues_in_slate,
    format_func=league_label,
    placeholder="Show all leagues",
)
if selected:
    sim = sim[sim["league_code"].isin(selected)]

with tb_settings:
    s1, s2 = st.columns(2)
    min_edge_pct = s1.slider("Min edge", 0.0, 15.0, 2.0, 0.5,
                              format="%.1f%%",
                              help="Show only markets with at least this much edge over Kalshi.")
    kelly_frac   = s2.selectbox("Kelly fraction", [0.10, 0.25, 0.50, 1.00],
                                 index=1,
                                 format_func=lambda x: {0.10: "1/10 (very safe)",
                                                          0.25: "1/4 (recommended)",
                                                          0.50: "1/2 (aggressive)",
                                                          1.00: "Full Kelly"}[x],
                                 help="A fraction of full Kelly to size each bet. "
                                       "Most disciplined bettors use 1/4 Kelly to dampen variance.")


# ---------------------------------------------------------------------------
# Build the picks table
# ---------------------------------------------------------------------------
def kelly_full(sim_p: float, kalshi_p: float) -> float:
    """Full Kelly fraction for a Kalshi YES @ kalshi_p with our true-prob sim_p.
    Returns 0 if no edge (we never recommend a bet against ourselves).
    Math: f* = p - q/b where b = (1-p_k)/p_k (profit per unit staked).
    """
    if sim_p <= kalshi_p or kalshi_p <= 0 or kalshi_p >= 1 or sim_p <= 0 or sim_p >= 1:
        return 0.0
    b = (1.0 - kalshi_p) / kalshi_p
    f = sim_p - (1.0 - sim_p) / b
    return max(0.0, f)


MIN_EDGE = min_edge_pct / 100.0  # convert percent to decimal

rows: list[dict] = []
for _, r in sim.iterrows():
    p_h = float(r["p_home_win"]); p_d = float(r["p_draw"]); p_a = float(r["p_away_win"])
    p_o25 = float(r.get("p_o_25") or 0)
    p_btts_v = float(r.get("p_btts") or 0)
    line = r.get("total_line")

    candidates = [
        ("ML_home",   f"{r['home']} ML",   r.get("yes_home_cents"), p_h,
            "ML_home", cal_ml),
        ("Draw",      "Draw",              r.get("yes_draw_cents"), p_d,
            "Draw",    cal_ml),
        ("ML_away",   f"{r['away']} ML",   r.get("yes_away_cents"), p_a,
            "ML_away", cal_ml),
        ("BTTS_yes",  "BTTS yes",          r.get("yes_btts_cents"), p_btts_v,
            "BTTS",    cal_btts),
    ]
    if pd.notna(line) and float(line) == 2.5:
        candidates.append(("Over_2.5", "Over 2.5", r.get("yes_over_cents"),
                            p_o25, "Over_2.5", cal_total))
        candidates.append(("Under_2.5", "Under 2.5", r.get("yes_under_cents"),
                            1.0 - p_o25, None, None))

    for market_code, market_label, cents, sim_p, cal_market, cal_table in candidates:
        kalshi_p = kalshi_implied(cents)
        if not np.isfinite(kalshi_p):
            continue
        edge = sim_p - kalshi_p
        if edge < MIN_EDGE:
            continue
        f_full   = kelly_full(sim_p, kalshi_p)
        units    = f_full * kelly_frac * 100.0  # 1u = 1% of bankroll
        if units <= 0:
            continue
        cal_text = ""
        if cal_market and cal_table is not None and not cal_table.empty:
            cal = calibrate_lookup(cal_table, cal_market, sim_p)
            if cal and int(cal.get("n_games", 0)) >= 10:
                cal_text = (f"sim {int(cal['pct'])}% → {int(cal['wins'])}-"
                            f"{int(cal['losses'])} ({cal['actual_rate']*100:.1f}%) "
                            f"over {int(cal['n_games']):,} games")
        rows.append({
            "Match":         f"{team_abbr(r['home'])} vs {team_abbr(r['away'])}",
            "Match (full)":  f"{r['home']} vs {r['away']}",
            "League":        league_label(r["league_code"]),
            "Market":        market_label,
            "Sim %":         sim_p * 100,
            "Kalshi ¢":      int(round(kalshi_p * 100)),
            "American":      cents_to_american(cents),
            "Edge %":        edge * 100,
            "Kelly %":       f_full * 100,
            "Units (rec.)":  units,
            "Calibration":   cal_text,
        })

picks_df = pd.DataFrame(rows)

if picks_df.empty:
    st.info(
        f"No edges at or above **{min_edge_pct:.1f}%** on the {date_str} slate. "
        "Lower the threshold above, or wait for the next live-prices refresh."
    )
    st.stop()


# ---------------------------------------------------------------------------
# Headline cards
# ---------------------------------------------------------------------------
n_picks      = len(picks_df)
total_units  = float(picks_df["Units (rec.)"].sum())
avg_edge     = float(picks_df["Edge %"].mean())
biggest_edge = float(picks_df["Edge %"].max())

c1, c2, c3, c4 = st.columns(4)
c1.markdown(
    f'<div class="stat-card"><div class="stat-label">Picks today</div>'
    f'<div class="stat-value">{n_picks}</div>'
    f'<div class="stat-caption">≥ {min_edge_pct:.1f}% edge</div></div>',
    unsafe_allow_html=True,
)
c2.markdown(
    f'<div class="stat-card"><div class="stat-label">Total recommended</div>'
    f'<div class="stat-value">{total_units:.1f}u</div>'
    f'<div class="stat-caption">across all markets</div></div>',
    unsafe_allow_html=True,
)
c3.markdown(
    f'<div class="stat-card"><div class="stat-label">Average edge</div>'
    f'<div class="stat-value">{avg_edge:+.1f}%</div>'
    f'<div class="stat-caption">across {n_picks} picks</div></div>',
    unsafe_allow_html=True,
)
c4.markdown(
    f'<div class="stat-card"><div class="stat-label">Biggest edge</div>'
    f'<div class="stat-value">{biggest_edge:+.1f}%</div>'
    f'<div class="stat-caption">single-pick max</div></div>',
    unsafe_allow_html=True,
)

st.markdown(" ")


# ---------------------------------------------------------------------------
# Picks table — sorted by units descending
# ---------------------------------------------------------------------------
display = picks_df.sort_values("Units (rec.)", ascending=False).copy()
display["Sim %"]        = display["Sim %"].round(1).astype(str) + "%"
display["Edge %"]       = display["Edge %"].apply(lambda v: f"+{v:.1f}%")
display["Kelly %"]      = display["Kelly %"].round(1).astype(str) + "%"
display["Units (rec.)"] = display["Units (rec.)"].round(2).astype(str) + "u"
display["Kalshi ¢"]     = display["Kalshi ¢"].astype(str) + "¢"

# Drop the helper full-name column for the visible table; keep Match (abbrev).
table = display[[
    "Match", "League", "Market", "Sim %", "Kalshi ¢", "American",
    "Edge %", "Kelly %", "Units (rec.)", "Calibration",
]].rename(columns={"Match": "Match"})

st.dataframe(
    table,
    width="stretch",
    hide_index=True,
    column_config={
        "Match":        st.column_config.TextColumn("Match", width="small"),
        "League":       st.column_config.TextColumn("League"),
        "Market":       st.column_config.TextColumn("Market", width="medium"),
        "Sim %":        st.column_config.TextColumn("Sim %"),
        "Kalshi ¢":     st.column_config.TextColumn("Kalshi"),
        "American":     st.column_config.TextColumn("Odds"),
        "Edge %":       st.column_config.TextColumn("Edge"),
        "Kelly %":      st.column_config.TextColumn("Full Kelly"),
        "Units (rec.)": st.column_config.TextColumn(
            f"Recommended (× {kelly_frac:.2f} Kelly)",
            help=("Suggested stake as a percent of bankroll. 1 unit = 1% of "
                   "bankroll. Computed as full Kelly × the fraction selected "
                   "in the toolbar."),
        ),
        "Calibration":  st.column_config.TextColumn(
            "Historical hit rate",
            help="From the 13.7K-match historical backtest, ±2.5% local window.",
        ),
    },
)


# ---------------------------------------------------------------------------
# Footer / explanation
# ---------------------------------------------------------------------------
st.divider()

with st.expander("How units & Kelly work here"):
    st.markdown(
        """
**Edge** = our calibrated probability for the outcome minus the Kalshi YES
implied probability. A +5% edge means we think the outcome is 5 percentage
points more likely than the market does.

**Full Kelly** is the bet fraction that maximizes long-run growth of bankroll
when our probability estimate is correct. It's also the *most aggressive*
sensible stake — get the probability wrong and Full Kelly hurts a lot more
than fractional Kelly.

**1 unit = 1% of your bankroll**, so a "2.3u" recommendation means stake 2.3%
of your bankroll on that market. The Kelly fraction selector in the toolbar
controls how aggressive the sizing is:

- **1/10 Kelly** — very low variance, slow growth (good if you're not 100%
  sure the calibration is well-tuned for the markets you bet on)
- **1/4 Kelly** — the standard "disciplined bettor" choice; a strong balance
  of growth and drawdown
- **1/2 Kelly** — meaningfully more aggressive
- **Full Kelly** — for backtesting only; live betting at full Kelly amplifies
  any model error

PITCH is research, not betting advice — sizing is shown for reference.
"""
    )

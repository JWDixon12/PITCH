"""Today's Slate page — calibrated probabilities + Kalshi edges per match."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import (
    available_dates, calibrate_lookup, edge_html, inject_global_css,
    kalshi_implied, league_label,
    load_calibration_btts, load_calibration_ml, load_calibration_total,
    load_kalshi, load_slate, today_ct_date,
)

st.set_page_config(page_title="Today's Slate · PITCH", page_icon="⚽", layout="wide")
inject_global_css()


# ---------------------------------------------------------------------------
# Date picker
# ---------------------------------------------------------------------------
dates = available_dates()
default = today_ct_date().isoformat()
if default not in dates and dates:
    default = dates[0]
elif not dates:
    dates = [default]

date_str = st.sidebar.selectbox("Slate date", dates,
                                 index=dates.index(default) if default in dates else 0)

st.markdown(
    f"""<div class="hero">
    <div class="hero-title">⚽ Today's Slate</div>
    <div class="hero-subtitle">{date_str} — calibrated sim probabilities + live Kalshi prices.</div>
    </div>""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
sim = load_slate(date_str)
kalshi = load_kalshi(date_str)
cal_ml = load_calibration_ml()
cal_total = load_calibration_total()
cal_btts = load_calibration_btts()

if sim.empty:
    st.warning(f"No matches in slate for {date_str}.")
    st.stop()

# Merge Kalshi (left join on fixture_id)
if not kalshi.empty:
    sim = sim.merge(kalshi, on="fixture_id", how="left")

# League filter
leagues_in_slate = sorted(sim["league_code"].unique())
selected = st.sidebar.multiselect(
    "Leagues", leagues_in_slate, default=leagues_in_slate,
    format_func=league_label,
)
sim = sim[sim["league_code"].isin(selected)] if selected else sim
sim = sim.sort_values("kickoff").reset_index(drop=True)

st.caption(f"{len(sim)} matches displayed")


# ---------------------------------------------------------------------------
# Match cards
# ---------------------------------------------------------------------------
def render_match(r: pd.Series):
    kickoff = pd.Timestamp(r["kickoff"])
    if kickoff.tzinfo:
        ko_local = kickoff.tz_convert("US/Central")
    else:
        ko_local = kickoff
    time_str = ko_local.strftime("%a %b %d  %I:%M %p CT")
    p_h, p_d, p_a = float(r["p_home_win"]), float(r["p_draw"]), float(r["p_away_win"])

    with st.container():
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.markdown(
                f"""<div class="match-card">
                <div class="match-meta">{time_str} · {league_label(r['league_code'])}</div>
                <div class="match-title">{r['home']} vs {r['away']}</div>
                <div style="margin-top:0.6rem;">
                  <span class="prob-h">{r['home']} {p_h*100:.1f}%</span> &nbsp;·&nbsp;
                  <span class="prob-d">Draw {p_d*100:.1f}%</span> &nbsp;·&nbsp;
                  <span class="prob-a">{r['away']} {p_a*100:.1f}%</span>
                </div>
                <div style="color:#8B949E;font-size:0.85rem;margin-top:0.4rem;">
                Most likely: <b style="color:#F0F6FC">{r['most_likely_score']}</b>
                &nbsp;&nbsp; Top: {r['top3_scores']}
                </div>
                <div style="color:#8B949E;font-size:0.85rem;margin-top:0.2rem;">
                Expected goals: {r['lambda_home']:.2f} – {r['lambda_away']:.2f}
                &nbsp;&nbsp; Total {r['expected_total_goals']:.2f}
                </div>
                </div>""",
                unsafe_allow_html=True,
            )

            # Calibration line
            cal_lines = []
            c = calibrate_lookup(cal_ml, "ML_home", p_h)
            if c is not None and c["n_games"] >= 10:
                cal_lines.append(
                    f"Sim {int(c['pct'])}% home → went "
                    f"<b>{int(c['wins'])}-{int(c['losses'])} ({c['actual_rate']*100:.1f}%)</b> "
                    f"over {int(c['n_games'])} historical games"
                )
            if not cal_total.empty and "Over_2.5" in cal_total["market"].values:
                c = calibrate_lookup(cal_total, "Over_2.5", float(r["p_o_25"]))
                if c is not None and c["n_games"] >= 10:
                    cal_lines.append(
                        f"Sim {int(c['pct'])}% O2.5 → went "
                        f"<b>{int(c['wins'])}-{int(c['losses'])} ({c['actual_rate']*100:.1f}%)</b> "
                        f"over {int(c['n_games'])} games"
                    )
            for line in cal_lines:
                st.markdown(f'<div class="calib-row">{line}</div>',
                             unsafe_allow_html=True)

        with col2:
            st.markdown("**Totals & props**")
            st.write(f"Over 1.5: **{r['p_o_15']*100:.1f}%**")
            st.write(f"Over 2.5: **{r['p_o_25']*100:.1f}%**")
            st.write(f"Over 3.5: **{r['p_o_35']*100:.1f}%**")
            st.write(f"BTTS yes: **{r['p_btts']*100:.1f}%**")
            st.write(f"Home CS: **{r['p_cs_home']*100:.1f}%**  ·  Away CS: **{r['p_cs_away']*100:.1f}%**")

        with col3:
            kh = kalshi_implied(r.get("yes_home_cents"))
            kd = kalshi_implied(r.get("yes_draw_cents"))
            ka = kalshi_implied(r.get("yes_away_cents"))
            ko_over = kalshi_implied(r.get("yes_over_cents"))
            kbtts = kalshi_implied(r.get("yes_btts_cents"))
            line = r.get("total_line")

            if any(np.isfinite(x) for x in [kh, kd, ka, ko_over, kbtts]):
                st.markdown("**Kalshi**")
                if np.isfinite(kh):
                    st.markdown(
                        f"Home {kh*100:.0f}¢ {edge_html(p_h - kh)}",
                        unsafe_allow_html=True,
                    )
                if np.isfinite(kd):
                    st.markdown(
                        f"Draw {kd*100:.0f}¢ {edge_html(p_d - kd)}",
                        unsafe_allow_html=True,
                    )
                if np.isfinite(ka):
                    st.markdown(
                        f"Away {ka*100:.0f}¢ {edge_html(p_a - ka)}",
                        unsafe_allow_html=True,
                    )
                if line is not None and pd.notna(line) and np.isfinite(ko_over) and float(line) == 2.5:
                    st.markdown(
                        f"O2.5 {ko_over*100:.0f}¢ {edge_html(float(r['p_o_25']) - ko_over)}",
                        unsafe_allow_html=True,
                    )
                if np.isfinite(kbtts):
                    st.markdown(
                        f"BTTS {kbtts*100:.0f}¢ {edge_html(float(r['p_btts']) - kbtts)}",
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown("**Kalshi**")
                st.caption("No live market for this match.")


for _, row in sim.iterrows():
    render_match(row)

st.divider()
st.caption(
    "Edges shown are simulator probability minus Kalshi implied probability. "
    "Positive = sim says more likely than market. "
    "PITCH is research; not betting advice."
)

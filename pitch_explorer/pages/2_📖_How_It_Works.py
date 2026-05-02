"""How It Works — public-facing methodology overview."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import inject_global_css

st.set_page_config(
    page_title="How It Works · PITCH",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_css()

st.markdown(
    """<div class="hero">
    <div class="hero-title">📖 How It Works</div>
    </div>""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
st.markdown(
    """
Every match prediction is built from layered evidence: team strength, recent
form, expected goals, lineups, head-to-head history, and market prices. PITCH
combines those signals into a calibrated probability for win, draw, and loss,
the most likely scoreline, and full totals + BTTS odds.

PITCH then compares those probabilities to the live Kalshi market. When PITCH
rates an outcome higher than the market does, that gap is logged as an edge.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# What goes in
# ---------------------------------------------------------------------------
st.markdown("## What goes into a prediction")

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        """
### ⚽ Team strength
For every team, PITCH estimates two ratings:

- How many goals they score per game vs an average opponent
- How many goals they concede per game vs an average opponent

Ratings rebuild every morning from the latest results, so a hot streak or a
defensive collapse moves them within days.

### 🌍 Cross-league comparison
A 13th-place EPL side meeting a 2nd-place Bundesliga side is a hard matchup
to model — the two leagues have different scoring environments. PITCH fits a
single model across all 7 competitions at once, with a per-league adjustment
so attacking and defensive ratings translate across borders. This is what
powers the UCL and UEL predictions.

### 📈 Expected goals (xG)
Goals alone are noisy. A 3-1 win can come from one deflection or from total
domination. Expected goals measure shot quality, so a side creating great
chances but finishing them poorly gets credited for the underlying play.

### ⏳ Recent form
Older matches still feed the model, but their weight decays over time.
Recent results carry far more weight than a 2-month-old result.
"""
    )

with c2:
    st.markdown(
        """
### 👥 Lineups & player availability
Predictions update once probable lineups are released. A missing top
striker, starting keeper, or three first-choice defenders changes the math.
When lineup data isn't available yet, the prediction shows that explicitly
rather than assume a full-strength team.

### 🧠 Managerial tactics
Different managers play different football. A team that's just hired a
high-press coach is not the team that played 20 games of low-block under
the previous regime. PITCH picks this up through the live ratings shifting
after a change, through how chances created and conceded move, and through
the tactical predictions it recalibrates against.

### 🏆 Head-to-head & venue
Some matchups defy the rating because of stylistic clashes or strong home
advantage. Head-to-head history and home advantage are explicit features
the model can use when they help, and ignore when they don't.

### 💰 Market wisdom
Closing odds from sharp markets are an information signal in their own
right. PITCH treats them as one input among many, weighted accordingly.
"""
    )

st.divider()


# ---------------------------------------------------------------------------
# How they combine
# ---------------------------------------------------------------------------
st.markdown("## How the signals combine")
st.markdown(
    """
Each signal has blind spots. xG is good at chance quality but blind to a
manager change. Form captures the last 8 weeks but doesn't know about a
fresh injury list. Market prices are sharp but not always right.

PITCH combines all of them. A stacking model trained on years of historical
predictions learns the right weight for each signal, and outputs a single
calibrated probability for each outcome. When the signals agree, confidence
is high. When they disagree, the prediction pulls toward neutral.

The output is what you see on Today's Slate: win, draw, and loss
probabilities, the most likely scoreline, and the full distribution of
totals and Both-Teams-To-Score odds.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------
st.markdown("## How calibration works")
st.markdown(
    """
A model that says 60% should win 60% of the time across many predictions.

Across a 13,708-match historical backtest, PITCH measures exactly that. When
the simulator said 60%, how often did the team win? When it said 75%, how
often was it right?

That's what the calibration sentence on each tile reports:

> When the sim says 65%, this has gone 142-79 (64.3%) over 221 games

It applies to every market on the slate: win, draw, totals, and BTTS.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# Daily refresh
# ---------------------------------------------------------------------------
st.markdown("## Daily refresh")
st.markdown(
    """
PITCH refreshes overnight:

1. Pulls the latest results, lineups, injuries, and ratings
2. Rebuilds team strength estimates
3. Re-validates calibration against the updated backtest
4. Simulates every game on today's slate (10,000 trials per match)
5. Pulls live Kalshi prices and computes edges
6. Grades yesterday's picks against actual scorelines

Live Kalshi prices refresh every 10 minutes during match days.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# Scope and disclaimer
# ---------------------------------------------------------------------------
st.markdown("## Validation")
st.markdown(
    """
PITCH has been tested against a **13,708-match historical backtest**. Every
backtest prediction was generated under live-match conditions — using only
the information available before kickoff — so the calibration numbers
reflect real forecasting performance, not curve-fitting after the fact. The
ratings, calibration table, and model itself retrain every morning on the
latest results.

Soccer is variance-heavy. Any single prediction can miss; the model's value
is in being right on average across hundreds of matches. PITCH is research,
not betting advice.
"""
)

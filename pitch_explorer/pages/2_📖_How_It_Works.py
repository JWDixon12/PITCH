"""How It Works — public-facing methodology overview (no math, no IP)."""
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
    initial_sidebar_state="collapsed",
)
inject_global_css()

# Hide the sidebar on this page too — same convention as the slate.
st.markdown(
    """
    <style>
      [data-testid="stSidebar"]            { display: none !important; }
      [data-testid="collapsedControl"]     { display: none !important; }
      [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """<div class="hero">
    <div class="hero-title">📖 How It Works</div>
    <div class="hero-subtitle">No black box. Here's what goes into every PITCH prediction — in plain English.</div>
    </div>""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# 30-second summary
# ---------------------------------------------------------------------------
st.markdown("## The 30-second version")
st.markdown(
    """
Every soccer match is a contest between attack and defence. PITCH learns each
team's attacking strength and each team's defensive strength from years of
results, then layers in **expected goals, market prices, lineups, form, and
head-to-head history** to refine the picture. The output is a calibrated
probability for win / draw / loss, the most likely scoreline, and full
totals + BTTS odds — every match, every day, automatically.

Then it watches the Kalshi market. When PITCH thinks a team is more likely to
win than the market does, that's an **edge**, and it gets logged.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# What goes in — the data ingredients
# ---------------------------------------------------------------------------
st.markdown("## What goes into a prediction")
st.markdown(
    "We don't bet on vibes. Every match prediction is built from layered "
    "evidence — here's what's actually feeding the model."
)

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        """
### ⚽ Team strength (offence × defence)
For every team across every league we track, PITCH estimates two numbers:

- **How many goals they score** per game vs an average opponent
- **How many goals they concede** per game vs an average opponent

These ratings rebuild every morning from the latest results, so a hot streak
or a defensive collapse moves the needle within days, not months.

### 🌍 Cross-league translation
A 13th-place EPL side meeting 2nd-place Bundesliga is hard for naive models,
because the two leagues live in different scoring environments. PITCH fits a
**single global model across all 7 competitions at once**, with a small
per-league adjustment so attacking and defensive ratings can be compared
directly across borders. This is what powers the UCL and UEL predictions.

### 📈 Expected goals (xG)
Goals are noisy — a 3-1 win can come from one lucky deflection, or from total
domination. Expected goals measure **shot quality**, not just outcomes. PITCH
ingests xG every match so a side that's been creating great chances but
finishing them poorly gets the credit they deserve.

### ⏳ Recent form
Today's Liverpool isn't last season's Liverpool. Older matches still feed the
model, but their weight decays over time — recent results matter much more
than a year-old result. The half-life is set so a team's form turning over
the last 6-8 weeks gets reflected without overreacting to a single bad day.
"""
    )

with c2:
    st.markdown(
        """
### 👥 Lineups & player availability
Predictions update once probable lineups are released. Missing your top
striker, your starting keeper, or three first-choice defenders changes the
math — and PITCH has signals for each (with a "we don't have lineup info
yet" indicator so we never silently pretend a full-strength side is playing).

### 🧠 Managerial tactics & shape
Different managers play different football. A team that's just hired a
high-press tactician is not the same team that played 20 games of low-block
under the previous regime. We pick this up indirectly: through the live
ratings shifting after the change, through how chances created and conceded
move, and through the API-Football tactical predictions we recalibrate
against.

### 🏆 Head-to-head & venue
Some matchups defy the rating. Atletico Madrid, at the Metropolitano, against
a particular opponent style, is its own story. Head-to-head history and home
advantage are explicit features the model can lean on when they actually
help — and ignore when they don't.

### 💰 Market wisdom
Closing odds from sharp markets (Pinnacle) are themselves an information
signal. PITCH doesn't blindly follow the market — but it knows the market is
right more often than wrong, and weights its own confidence accordingly.
"""
    )

st.divider()


# ---------------------------------------------------------------------------
# How they combine
# ---------------------------------------------------------------------------
st.markdown("## How those signals combine")
st.markdown(
    """
None of those signals is perfect on its own. xG is great for chance quality
but blind to recent injuries. Form is great for the last 8 weeks but doesn't
know about a manager change three days ago. Market prices are sharp but not
always right.

So PITCH combines them. A small **stacking model** — trained on years of
historical predictions — learns the right weight for each signal in each
situation, and produces a single calibrated probability per outcome. When
xG and the market and recent form all agree, confidence is high. When they
disagree, the model knows that and pulls the prediction toward neutral.

The output is what you see on **Today's Slate**: win / draw / loss
percentages, the most likely scoreline, and the full distribution of totals
and Both-Teams-To-Score odds.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------
st.markdown("## How we know it's working")
st.markdown(
    """
A model that says **60%** should win 60% of the time. Not 50%, not 70%.

To check this honestly, every prediction is logged. Across the **13,708-match
historical backtest** that PITCH was tuned against, we measure exactly that:
when the simulator said 60%, how often did the team actually win? When it
said 75%, how often was it right?

Those numbers are what you see in the calibration blurbs on the slate:

> *When the sim says 65%, this has gone 142-79 (64.3%) over 221 games*

It's a direct, evidence-based answer to the question "should I trust this
percentage?" — not just on win/loss, but on **draws, overs, unders, and BTTS
markets** too.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# Daily refresh
# ---------------------------------------------------------------------------
st.markdown("## How fresh is fresh")
st.markdown(
    """
PITCH refreshes itself completely overnight:

1. Pulls the latest results, lineups, injuries, and ratings
2. Rebuilds team strength estimates with the new data
3. Re-validates calibration against the updated backtest
4. Simulates every game on today's slate (10,000 trials per match)
5. Pulls live Kalshi prices and computes edges
6. Grades any picks from yesterday against actual scorelines

By the time you look at the slate, every number on it reflects the most
recent information available. Live Kalshi prices refresh every 10 minutes
during match days.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# What this is and isn't
# ---------------------------------------------------------------------------
st.markdown("## What PITCH is and isn't")

c3, c4 = st.columns(2)
with c3:
    st.markdown(
        """
### ✅ What it is
- A research project on whether soccer markets can be modelled out-of-sample
- Calibrated against **13,708 matches** across 7 competitions
- Fully out-of-sample — every backtest number was generated using only
  data available *before* each match was played
- Refreshed every morning, fully automatically
- Honest about its uncertainty — when calibration is thin or sample size
  is small, the blurb hides itself rather than mislead
"""
    )
with c4:
    st.markdown(
        """
### ❌ What it isn't
- **Betting advice.** PITCH is research and analysis; what you do with it is
  your own decision.
- A guaranteed money-maker. Pinnacle's closing line is sharper than us in the
  top-5 leagues — that's expected. The interesting question is the rest of
  the market.
- A black box. Every signal listed above feeds the prediction. There's no
  hidden secret sauce — just disciplined modelling on good data.
- Static. The model retrains every morning with the freshest results, and the
  calibration table grows every week.
"""
    )

st.divider()
st.caption(
    "Soccer is variance-heavy. Predictions reflect the model's best estimate "
    "given the information available at the time — they are not certainties. "
    "PITCH is research, not betting advice."
)

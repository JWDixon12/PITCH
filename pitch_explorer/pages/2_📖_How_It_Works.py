"""How It Works — public-facing methodology overview for the player-aware model."""
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
    <div class="hero-subtitle">A player-aware Poisson model — every match prediction is built up from
    the actual eleven names in the lineup, the manager picking them, and the team's strength under
    that manager's tenure.</div>
    </div>""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# TL;DR
# ---------------------------------------------------------------------------
st.markdown(
    """
PITCH doesn't treat a team as one rating that goes up and down. It treats a
match as the outcome of two specific lineups, picked by two specific managers,
playing for two specific clubs. The model predicts how many goals each side
will score by adding up:

- A baseline goal rate for the league
- A home advantage
- The home team's strength under their **current manager's spell**
- The away team's strength under their **current manager's spell**
- An attacking contribution from each home player who started, plus a
  defensive contribution from each away player who started — and vice versa

Once we have those two goal rates, we run 10,000 Monte Carlo simulations of
the match and read off the win/draw/loss split, the most likely scorelines,
and the over/BTTS distribution. Then we compare the resulting probabilities
to live Kalshi prices and surface the ones where there's a meaningful gap.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
st.markdown("## What goes into a goal rate")

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        """
### 🧠 Manager spells, not just teams
Football is coach-driven. A high-press Klopp Liverpool is not a Slot Liverpool
even with the same players. We split each team's history into **manager
spells** — every distinct coaching tenure becomes its own latent strength
parameter. The day a manager is sacked, the team's "spell" rolls over to a
new entry that starts from a shrunken prior and learns fast as new results
come in.

We currently track **2,600+ manager spells** across the leagues we cover.

### 👥 Per-player attack & defense
Every player who has started a match in our window gets two numbers:

- An **attack coefficient** — how much their presence raises the goals their
  team is expected to score
- A **defense coefficient** — how much their presence lowers the goals their
  team is expected to concede

These are partial effects, holding manager spell and team strength constant —
so they isolate the player's contribution rather than the club's. A
midfielder who creates chances has a positive attack coef. A center-back who
shuts down the box has a positive defense coef.

There are **51,000+ players** with fitted coefficients across the model.

### ⚽ The team-level latent
On top of the manager-spell strength sits a per-team baseline that captures
the parts of the club that don't move with managers — academy depth, scouting
quality, ownership stability, stadium effects. It's small relative to the
spell + lineup terms, but it's there.
"""
    )

with c2:
    st.markdown(
        """
### ⏳ Time-decay weights
Older matches still inform the fit, but their weight halves every **540 days**.
A goal scored last weekend counts roughly twice as much as one from 18 months
ago, and four times as much as one from three years ago. This means a young
striker who exploded in the last six months gets credited for it; a veteran
who's tailed off doesn't keep his old number.

### 🛑 Shrinkage so thin data doesn't lie
A player with 60 starts gets a real, opinionated coefficient. A player with
4 starts gets an L2-shrunken coefficient that's pulled hard toward zero.
This stops the model from over-reacting to a tiny sample — a deflected goal
from a backup striker doesn't suddenly make him look like Haaland.

The same shrinkage is applied to manager spells — a coach 3 games into the
job is mostly priced as "average for that league" until the evidence
accumulates.

### 🤝 Dixon-Coles low-score correction
Plain Poisson models slightly under-predict 0-0, 1-0, 0-1, and 1-1, and
slightly over-predict 1-1's neighbors. We apply the standard Dixon-Coles
correction so the resulting scoreline distribution lines up with what
actually happens in tight games.

### 🌍 Cross-league fitting
The strength scale is shared across competitions, so a Premier League side
can be compared to a Bundesliga side and a Ligue 1 side on a common axis.
This is what powers UCL and UEL predictions, and what lets us project a
Liverpool-Bayern game without pretending one league's "average" is the
same as another's.
"""
    )

st.divider()


# ---------------------------------------------------------------------------
# Lineups
# ---------------------------------------------------------------------------
st.markdown("## Why lineups matter — and what we do before they're posted")
st.markdown(
    """
Until both starting elevens are confirmed by API-Football (typically 60-90
minutes before kickoff), we **project** the lineup using:

1. The team's recent starters under the current manager
2. Each player's appearance frequency in those starts
3. Rotation hints from fixture density (UCL midweek + weekend league = expect
   rotation in the weakest of the two matches)

The slate badges each match accordingly:

- **PRELIMINARY** (amber) means we used a projected XI. The prediction is
  still a real prediction, but it'll move once the official sheet drops.
- **FINAL SIM** (green) means both XIs are confirmed and the sim has been
  re-run with the actual eleven on each side.

A background process scans for confirmed lineups every 10 minutes during
match days. The moment both XIs are in, the relevant matches re-sim in
seconds and flip to FINAL — without waiting for the next morning's
refresh.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# From goal rates to probabilities
# ---------------------------------------------------------------------------
st.markdown("## From goal rates to win/draw/loss")
st.markdown(
    """
The model produces two numbers per match: an expected home goal rate (λ_home)
and an expected away goal rate (λ_away). Those aren't predictions of what
will happen — they're predictions of the **distribution** of what could
happen.

We then run **10,000 Monte Carlo trials** per match, drawing scorelines from
that distribution (with the Dixon-Coles correction applied). The output is
not a single answer; it's a frequency table:

- How often does each side win?
- How often is the match a draw?
- How often does it go over 2.5? Over 3.5? Both teams to score?
- What are the three most likely exact scorelines?

That table is what becomes the win-probability bar, the totals box, the BTTS
box, and the scoreline ticker on each match card.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------
st.markdown("## Calibration — does 65% mean 65%?")
st.markdown(
    """
A model that says 60% should win 60% of the time across many predictions, or
the probabilities are misleading. We test that explicitly with a
**walk-forward backtest**: every prediction in the calibration table was
generated using only the information available **before** kickoff, then
graded against the actual result.

That's what the italicized line under each tile reports:

> When the sim says 65%, this has gone 142-79 (64.3%) over 221 games.

If the historical bucket nearest to a sim's probability is more than 5
percentage points away (because we've never seen a sim that confident on,
say, an Over 4.5 line), the calibration sentence is hidden rather than
extrapolated.

Calibration tables exist for **moneyline, totals (Over/Under each half-goal
line), and Both-Teams-To-Score** — every market we surface on the slate.
"""
)

st.divider()


# ---------------------------------------------------------------------------
# Refresh cadence
# ---------------------------------------------------------------------------
st.markdown("## Refresh cadence")
st.markdown(
    """
**Every morning at 5:00 AM CT** (the heavy refresh):

1. Pull the latest results from the past 24 hours
2. Pull the next 3 days of fixtures across every league we cover
3. Refit the player-aware model with the updated history
4. Rebuild the calibration tables from a fresh walk-forward backtest
5. Sim every fixture in the 3-day window with **projected XIs** (PRELIMINARY)
6. Pull Kalshi prices for the same 3-day window
7. Run the picker — surface every game with at least a 3% edge

**Every 10 minutes during match days, 06:00-23:50 CT** (the live refresh):

1. Re-pull lineups from API-Football
2. Re-sim any preliminary fixture whose XIs are now confirmed → flip to FINAL
3. Re-pull Kalshi — but freeze prices for any fixture that's already kicked
   off so live in-play swings don't overwrite the locked pre-match line
4. Re-run the picker so new edges show up the moment a confirmed XI changes
   the math

**Every match day**: yesterday's picks get graded against the actual
scorelines and the running record updates.
"""
)

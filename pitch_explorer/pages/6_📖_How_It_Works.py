"""How It Works — methodology in plain English."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import inject_global_css

st.set_page_config(page_title="How It Works · PITCH", page_icon="📖", layout="wide")
inject_global_css()

st.markdown(
    """<div class="hero">
    <div class="hero-title">📖 How It Works</div>
    <div class="hero-subtitle">No black box. Here's exactly what PITCH does and why.</div>
    </div>""",
    unsafe_allow_html=True,
)

st.markdown(
    """
## The 30-second version

Every match between two soccer teams is a contest between attack and defence.
PITCH learns each team's attacking strength and each team's defensive
strength from years of past results, mixes in extra signals (xG, market
prices, lineups, form, head-to-head, Elo), and turns the whole thing into
**probabilities** for win / draw / loss, the **most likely scoreline**, and
**totals / BTTS** odds.

Then it watches Kalshi. When PITCH thinks a team is more likely to win than
the market does, that's an **edge** — and it gets logged.
"""
)

st.divider()

st.markdown(
    """
## Step 1 — The base model: goal-Poisson with Dixon-Coles

Goals in soccer are **rare and roughly independent** — and that means they
follow a Poisson distribution. So we fit two numbers per team:

- **`atk[team]`** — how many goals they tend to score per game (relative to league average)
- **`def[team]`** — how many goals they tend to concede per game (relative to league average)

…plus a global **home-field advantage** `γ`. The expected goals per side become:

```
λ_home = exp( μ + atk[home] − def[away] + γ )
λ_away = exp( μ + atk[away] − def[home]     )
```

Once we know both `λ`s, we can compute the probability of every scoreline
(0-0, 1-0, 1-1, 2-1, …) up to 12 goals per side.

### Dixon-Coles low-score correction

Pure Poisson slightly **under-counts 0-0, 1-0, 0-1 and 1-1**, because in real
soccer scores aren't truly independent — late game-state effects nudge toward
those low draws and one-goal games. Dixon-Coles' famous correction `τ(home, away, λ_h, λ_a, ρ)`
multiplies those four cells, with `ρ` fit to historical data. It's small but
material — it pushes calibration on draws by ~1 percentage point in the
right direction.
"""
)

st.divider()

st.markdown(
    """
## Step 2 — Cross-league translation: global Poisson with league offsets

Per-league models can't tell you what happens when 13th-place EPL Brentford
plays 2nd-place Bundesliga Bayer Leverkusen — they've never met, and the two
leagues have different scoring environments.

**Solution:** fit one big global model across **all 7 leagues at once**, with
a small additive offset per league:

```
λ_home = exp( μ + atk[home] − def[away] + γ
              + 0.5·(L_off[home_league] + L_off[away_league]) )
```

Now Bundesliga's higher base scoring rate sits in `L_off["D1"]`, and Brentford's
attack and Bayer's defence are directly comparable. On the **UCL + UEL backtest
subset (n=1,711)** this model posts a Brier of **0.5924** — the best of any
model on cross-league matches.
"""
)

st.divider()

st.markdown(
    """
## Step 3 — Stacking: combine everything

The goal-Poisson is one signal. We have several others:

| Signal | Source |
|---|---|
| **Per-league goal-Poisson + DC** | One model per league, more sensitive to local form |
| **Global goal-Poisson + offsets** | The cross-league translator |
| **Global xG-Poisson** | Same idea, but using expected-goals (post-shot quality) |
| **API-Football recalibration** | Their winner predictions, recalibrated to a logreg |
| **API-Football direct probabilities** | Their probabilities as-is |
| **Pinnacle de-vigged closing** | What the sharpest market thought |
| **Elo + form + h2h + lineups** | Engineered features with `_missing` indicators |

A **stacking logistic regression** learns the right weight for each signal —
walk-forward over time, with a 120-day half-life on weights so older matches
fade. The output is a final calibrated `(p_home, p_draw, p_away)`.
"""
)

st.divider()

st.markdown(
    """
## Step 4 — Walk-forward backtest (no peeking)

Every prediction in the **Backtest** tab was made using only data **available
before kickoff**. We train on everything up to date `T-1`, predict matches on
date `T`, then roll forward. No future leakage. The 13,708 predictions you
see span 2019-06 → 2025-05.
"""
)

st.divider()

st.markdown(
    """
## Step 5 — Monte Carlo for scorelines and totals

Once we have `λ_home` and `λ_away`, we run **10,000 simulated matches** per
fixture:

- Sample home goals ~ Poisson(λ_home), away goals ~ Poisson(λ_away)
- Apply the Dixon-Coles correction to draw the joint distribution
- Tally how often each scoreline happens

That gives us:

- **Most likely scoreline** + top 3 alternatives
- **Win / draw / loss** probabilities
- **Over / Under 1.5, 2.5, 3.5** probabilities
- **Both Teams To Score (BTTS)** probability
- **Clean sheet** probabilities for both sides
"""
)

st.divider()

st.markdown(
    """
## Step 6 — Calibration: "when sim says 60%, did it really go 6-4?"

A model that says 60% should win 60% of the time. The **Calibration tab**
shows this empirically across the 13.7K-match backtest, bucket by bucket:

> Sim 65% home → went 142-79 (64.3%) over 221 historical games

For each market — match outcome, total goals, BTTS — we sweep every integer
percent from 0 to 100, take a ±2.5% bandwidth window of historical
predictions at that level, and report the actual hit rate. If our 60% buckets
have actually gone closer to 50%, the calibration plot makes it obvious.
"""
)

st.divider()

st.markdown(
    """
## Step 7 — Edges vs Kalshi, and the picks log

Kalshi sells YES contracts on each outcome priced in **cents** (45¢ = 45%
implied probability, paying $1 if it hits). Every morning:

1. We compute our calibrated probabilities for the slate
2. We pull live Kalshi prices for the same matches
3. For each market with `our_prob − kalshi_implied ≥ 3%`, we log a pick

That's it — no Kelly, no bankroll engine. **Flat 1u of capital staked**, and
profits compounded honestly:

```
WIN at YES @ X¢   →   profit = (100 − X) / X    units
LOSS              →   profit = −1u
```

The **Picks Tracker tab** shows lifetime W-L, ROI, and per-market hit rate
graded against actual results.
"""
)

st.divider()

st.markdown(
    """
## What PITCH is and isn't

**It is:**
- A research project on whether soccer markets can be modeled out-of-sample
- Fully out-of-sample, walk-forward — every backtest number is honest
- Calibrated against 13.7K matches across 7 competitions

**It isn't:**
- Betting advice
- A guaranteed money-maker (Pinnacle's closing line is sharper than us on
  top-5 leagues — that's expected, that's why they're Pinnacle)
- A black box (every step is documented above)

If a `+8% edge` shows on the slate, it means our calibrated probability is 8
percentage points higher than the Kalshi implied probability for that
contract. Whether that edge survives variance over a season is the open
question this project tries to answer honestly.
"""
)

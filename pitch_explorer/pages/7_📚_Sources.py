"""Sources — credits for the data PITCH stands on."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import inject_global_css

st.set_page_config(page_title="Sources · PITCH", page_icon="📚", layout="wide")
inject_global_css()

st.markdown(
    """<div class="hero">
    <div class="hero-title">📚 Sources</div>
    <div class="hero-subtitle">Every number in PITCH ultimately comes from these.</div>
    </div>""",
    unsafe_allow_html=True,
)

st.markdown("## Data sources")

c1, c2 = st.columns(2)

with c1:
    st.markdown(
        """
### API-FOOTBALL
**[api-football.com](https://www.api-football.com/)**

The backbone of the model. Provides:
- Fixtures, lineups, statistics, events, predictions, injuries, coach data
- Historical coverage 2019 → present across all 7 competitions tracked
- ~57,000 fixtures cached locally; refreshed daily for the current season

Used for: per-match expected goals (where coverage exists 2022+), starting
lineups, formation data, lineup-level injury signals, and the recalibration
target for the API-FB direct prediction model.

### Kalshi
**[kalshi.com](https://kalshi.com/)**

The live market we compare against. CFTC-regulated event-contract exchange
with weekly soccer markets across most major competitions:

- 3-way moneyline (KXSOC* / KXEPL* / KXLAL* / KXSER* / KXBUN* / KXLIG* / KXMLS* / KXUCL* / KXUEL*)
- Over / Under total goals (line is whichever YES contract trades closest to 50¢)
- Both Teams To Score (BTTS)

PITCH's "edge" column is **simulator probability − Kalshi implied
probability**.
"""
    )

with c2:
    st.markdown(
        """
### football-data.co.uk (FDCOUK)
**[football-data.co.uk](https://www.football-data.co.uk/)**

The historical results + closing line archive. Provides Pinnacle de-vigged
closing prices that we use as the **sharpness benchmark** in the backtest.
This is the toughest possible test — Pinnacle's late closing line is the
world's most informed price after every lineup announcement, late injury,
and weather check.

### ClubElo
**[clubelo.com](http://clubelo.com/)**

Daily-updating club Elo ratings. Used as a stacking feature, both raw and as
**Elo difference** between sides.

### Understat
**[understat.com](https://understat.com/)**

Per-shot xG data for the top-5 European leagues, providing an alternate xG
ground truth used in the **xG-Poisson** auxiliary model.

### Internal: walk-forward training set
- 13,708 matches across **EPL · LaLiga · Serie A · Bundesliga · Ligue 1 · UCL · UEL · MLS**
- Every prediction trained only on data **before the match was played**
- Time-decay weighting (120-day half-life) on training observations
"""
    )

st.divider()

st.markdown(
    """
## How the daily refresh works

```
3:30 AM CT  →  pull yesterday's results + today's fixtures from API-FOOTBALL
            →  rebuild unified_master.parquet
            →  refit per-league + global Poissons on the rolling window
            →  Monte Carlo simulate today's slate (n=10,000 per match)
            →  fetch live Kalshi markets
            →  log new edges ≥ 3% to picks_history
            →  grade yesterday's pending picks against actual scorelines
            →  push fresh parquets so this Streamlit app updates
```

Live Kalshi prices refresh every 10 minutes during match days.
"""
)

st.divider()

st.markdown(
    """
## License & disclaimer

All upstream data is used in accordance with each provider's terms of
service for personal research. Pinnacle closing lines are public and
historical. API-FOOTBALL access is on a paid Ultra subscription. Kalshi
data is public via their public REST API.

PITCH is a research project. **Not betting advice.** Predictions reflect
the model's view at the time they were generated and carry inherent
uncertainty. Soccer is variance-heavy by nature.
"""
)

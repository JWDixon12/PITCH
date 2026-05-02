"""Shared helpers for PITCH Streamlit pages."""
from __future__ import annotations

from pathlib import Path
from datetime import date as _date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "output"
TODAY_DIR = OUT / "today_matchups"

CT = timezone(timedelta(hours=-5))

LEAGUE_NAMES = {
    "E0":  "Premier League",
    "SP1": "La Liga",
    "I1":  "Serie A",
    "D1":  "Bundesliga",
    "F1":  "Ligue 1",
    "UCL": "Champions League",
    "UEL": "Europa League",
    "MLS": "Major League Soccer",
}

LEAGUE_FLAGS = {
    "E0":  "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "SP1": "🇪🇸",
    "I1":  "🇮🇹",
    "D1":  "🇩🇪",
    "F1":  "🇫🇷",
    "UCL": "🏆",
    "UEL": "🥈",
    "MLS": "🇺🇸",
}


def today_ct_date() -> _date:
    return datetime.now(CT).date()


def inject_global_css() -> None:
    """One-shot global CSS — keep it minimal so it doesn't fight Streamlit's
    own theme.toml.  All colours come from .streamlit/config.toml."""
    st.markdown(
        """
        <style>
        .hero {
            padding: 1.4rem 1.6rem 1rem 1.6rem;
            border-radius: 14px;
            background: linear-gradient(135deg, #11181F 0%, #0E1117 100%);
            border: 1px solid #1F2933;
            margin-bottom: 1.4rem;
        }
        .hero-title { font-size: 1.85rem; font-weight: 700; color: #F0F6FC; }
        .hero-subtitle { color: #8B949E; font-size: 0.95rem; margin-top: 0.2rem; }

        .stat-card {
            padding: 1rem 1.2rem;
            border-radius: 12px;
            background: #161B22;
            border: 1px solid #1F2933;
            text-align: center;
        }
        .stat-label { color: #8B949E; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; }
        .stat-value { color: #00C896; font-size: 1.6rem; font-weight: 700; margin-top: 0.2rem; }
        .stat-caption { color: #8B949E; font-size: 0.78rem; margin-top: 0.2rem; }

        .match-card {
            padding: 1.1rem 1.3rem;
            border-radius: 12px;
            background: #11181F;
            border: 1px solid #1F2933;
            margin-bottom: 0.9rem;
        }
        .match-meta { color: #8B949E; font-size: 0.85rem; margin-bottom: 0.4rem; }
        .match-title { color: #F0F6FC; font-size: 1.15rem; font-weight: 600; }
        .prob-h { color: #58A6FF; font-weight: 700; }
        .prob-d { color: #C9D1D9; }
        .prob-a { color: #FF7B72; font-weight: 700; }
        .edge-pos { color: #3FB950; font-weight: 700; }
        .edge-neg { color: #F85149; }

        .calib-row { color: #8B949E; font-size: 0.85rem; margin-top: 0.3rem; font-style: italic; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300)
def available_dates() -> list[str]:
    if not TODAY_DIR.exists():
        return []
    return sorted([p.name for p in TODAY_DIR.iterdir() if p.is_dir()],
                   reverse=True)


@st.cache_data(ttl=300)
def load_slate(date_str: str) -> pd.DataFrame:
    p = TODAY_DIR / date_str / "sim_lines.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


@st.cache_data(ttl=120)
def load_kalshi(date_str: str) -> pd.DataFrame:
    p = TODAY_DIR / date_str / "kalshi_markets.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


@st.cache_data(ttl=300)
def load_picks(date_str: str) -> pd.DataFrame:
    p = TODAY_DIR / date_str / "picks.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


@st.cache_data(ttl=600)
def load_calibration_ml() -> pd.DataFrame:
    p = OUT / "calibration_ml.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=600)
def load_calibration_total() -> pd.DataFrame:
    p = OUT / "calibration_total.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=600)
def load_calibration_btts() -> pd.DataFrame:
    p = OUT / "calibration_btts.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=600)
def load_picks_history() -> pd.DataFrame:
    p = OUT / "picks_history.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=600)
def load_backtest_summary() -> str:
    p = OUT / "backtest" / "unified_summary.txt"
    return p.read_text(encoding="utf-8") if p.exists() else ""


@st.cache_data(ttl=600)
def load_backtest_predictions() -> pd.DataFrame:
    p = OUT / "backtest" / "unified_predictions.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def calibrate_lookup(cal: pd.DataFrame, market: str, pct: float) -> dict | None:
    """Nearest calibration row for a given probability + market."""
    if cal is None or cal.empty:
        return None
    sub = cal[cal["market"] == market]
    if sub.empty:
        return None
    target = int(round(pct * 100))
    if target in sub["pct"].values:
        return sub[sub["pct"] == target].iloc[0].to_dict()
    diff = (sub["pct"] - target).abs()
    return sub.loc[diff.idxmin()].to_dict()


def kalshi_implied(cents) -> float:
    """Convert Kalshi YES price (cents) to implied probability."""
    if cents is None or pd.isna(cents):
        return float("nan")
    try:
        return float(cents) / 100.0
    except (TypeError, ValueError):
        return float("nan")


def edge_html(edge: float) -> str:
    """Format an edge as +X.X% or -X.X% with colour class."""
    if edge >= 0:
        return f'<span class="edge-pos">+{edge*100:.1f}%</span>'
    return f'<span class="edge-neg">{edge*100:.1f}%</span>'


def league_label(code: str) -> str:
    name = LEAGUE_NAMES.get(code, code)
    flag = LEAGUE_FLAGS.get(code, "")
    return f"{flag} {name}".strip()


def last_updated_text() -> str:
    """Look at the most recent slate dir to estimate the last update."""
    dates = available_dates()
    if not dates:
        return "no data yet"
    latest = TODAY_DIR / dates[0]
    sim = latest / "sim_lines.parquet"
    if sim.exists():
        ts = datetime.fromtimestamp(sim.stat().st_mtime)
        return f"slate for {dates[0]} (refreshed {ts.strftime('%Y-%m-%d %H:%M')})"
    return f"slate for {dates[0]}"

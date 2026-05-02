"""Shared helpers for PITCH Streamlit pages."""
from __future__ import annotations

import base64
from pathlib import Path
from datetime import date as _date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT       = REPO_ROOT / "output"
TODAY_DIR = OUT / "today_matchups"
DATA_PROC = REPO_ROOT / "data" / "processed"
LOGO_DIR  = Path(__file__).resolve().parent / "assets" / "logos"

# Fixed-offset Central — avoids the zoneinfo / tzdata dance on Streamlit Cloud.
# CT is UTC-5 in DST (most of the soccer season) and UTC-6 in winter; the
# slate header just shows times for human reference, so a fixed offset is fine.
CT = timezone(timedelta(hours=-5))


# ---------------------------------------------------------------------------
# League metadata
# ---------------------------------------------------------------------------
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

# Per-league accent colors used for the gradient game header.
LEAGUE_COLORS = {
    "E0":  "#3D195B",  # EPL purple
    "SP1": "#FF4B44",  # LaLiga red
    "I1":  "#008FD7",  # Serie A blue
    "D1":  "#D20515",  # Bundesliga red
    "F1":  "#091C3E",  # Ligue 1 navy
    "UCL": "#001A4F",  # UCL navy
    "UEL": "#F7A91E",  # UEL orange
    "MLS": "#1A3668",  # MLS blue
}


def league_label(code: str) -> str:
    name = LEAGUE_NAMES.get(code, code)
    flag = LEAGUE_FLAGS.get(code, "")
    return f"{flag} {name}".strip()


def league_color(code: str) -> str:
    return LEAGUE_COLORS.get(code, "#5865F2")


# Manual abbreviations for the well-known clubs. Falls back to the heuristic
# in ``team_abbr`` for everything else (still produces a sensible 3-letter
# code, just not the broadcast-standard one).
TEAM_ABBR_OVERRIDES = {
    # Premier League
    "Arsenal": "ARS", "Aston Villa": "AVL", "Bournemouth": "BOU",
    "Brentford": "BRE", "Brighton": "BHA", "Burnley": "BUR",
    "Chelsea": "CHE", "Crystal Palace": "CRY", "Everton": "EVE",
    "Fulham": "FUL", "Ipswich": "IPS", "Leeds": "LEE",
    "Leicester": "LEI", "Liverpool": "LIV", "Luton": "LUT",
    "Manchester City": "MCI", "Manchester United": "MUN",
    "Newcastle": "NEW", "Nottingham Forest": "NFO", "Sheffield Utd": "SHU",
    "Southampton": "SOU", "Sunderland": "SUN", "Tottenham": "TOT",
    "West Ham": "WHU", "Wolves": "WOL",
    # La Liga
    "Real Madrid": "RMA", "Barcelona": "BAR", "Atletico Madrid": "ATM",
    "Athletic Club": "ATH", "Real Sociedad": "RSO", "Real Betis": "BET",
    "Villarreal": "VIL", "Valencia": "VAL", "Sevilla": "SEV",
    "Celta Vigo": "CEL", "Osasuna": "OSA", "Mallorca": "MLL",
    "Girona": "GIR", "Getafe": "GET", "Las Palmas": "LPA",
    "Rayo Vallecano": "RAY", "Espanyol": "ESP", "Alaves": "ALA",
    "Levante": "LEV", "Elche": "ELC", "Cadiz": "CAD",
    "Valladolid": "VLL", "Leganes": "LEG", "Granada": "GRA",
    "Almeria": "ALM",
    # Serie A
    "Juventus": "JUV", "Inter": "INT", "AC Milan": "MIL", "Milan": "MIL",
    "Napoli": "NAP", "Roma": "ROM", "Lazio": "LAZ",
    "Atalanta": "ATA", "Fiorentina": "FIO", "Bologna": "BOL",
    "Torino": "TOR", "Udinese": "UDI", "Sassuolo": "SAS",
    "Genoa": "GEN", "Lecce": "LEC", "Cagliari": "CAG",
    "Hellas Verona": "VER", "Verona": "VER", "Empoli": "EMP",
    "Monza": "MON", "Como": "COM", "Parma": "PAR",
    "Venezia": "VEN", "Pisa": "PIS", "Cremonese": "CRE",
    "Salernitana": "SAL", "Frosinone": "FRO",
    # Bundesliga
    "Bayern München": "BAY", "Bayern Munich": "BAY",
    "Borussia Dortmund": "BVB", "RB Leipzig": "RBL",
    "Bayer Leverkusen": "B04", "Eintracht Frankfurt": "SGE",
    "VfB Stuttgart": "VFB", "Stuttgart": "VFB",
    "Borussia Mönchengladbach": "BMG", "Werder Bremen": "BRE",
    "FC Augsburg": "FCA", "Augsburg": "FCA",
    "VfL Wolfsburg": "WOB", "Wolfsburg": "WOB",
    "1. FC Köln": "KOE", "FC Köln": "KOE", "1. FSV Mainz 05": "M05",
    "Mainz": "M05", "TSG Hoffenheim": "TSG", "Hoffenheim": "TSG",
    "SC Freiburg": "SCF", "Freiburg": "SCF",
    "Union Berlin": "FCU", "Hertha Berlin": "BSC",
    "FC St. Pauli": "STP", "St. Pauli": "STP",
    "Hamburger SV": "HSV", "Holstein Kiel": "KIE", "Heidenheim": "HEI",
    "1. FC Heidenheim": "HEI", "VfL Bochum": "BOC", "Bochum": "BOC",
    "Darmstadt": "SVD",
    # Ligue 1
    "Paris Saint Germain": "PSG", "Paris Saint-Germain": "PSG",
    "Marseille": "OM",  "Lyon": "OL", "Olympique Lyonnais": "OL",
    "Monaco": "ASM", "AS Monaco": "ASM", "Lille": "LIL",
    "Nice": "NIC", "Stade Rennais": "REN", "Rennes": "REN",
    "Lens": "LEN", "Strasbourg": "STR", "Toulouse": "TFC",
    "Nantes": "FCN", "Reims": "RMS", "Montpellier": "MTP",
    "Brest": "BRE", "Auxerre": "AUX", "Angers": "SCO",
    "Le Havre": "HAC", "Saint Etienne": "ASS", "Saint-Etienne": "ASS",
    "AS Saint-Étienne": "ASS",
    # MLS (selected)
    "LAFC": "LAFC", "LA Galaxy": "LAG", "Inter Miami": "MIA",
    "Atlanta United": "ATL", "Seattle Sounders": "SEA",
    "Portland Timbers": "POR", "New York Red Bulls": "RBNY",
    "New York City FC": "NYC", "Toronto FC": "TOR",
    "Vancouver Whitecaps": "VAN", "Columbus Crew": "CLB",
    "FC Cincinnati": "CIN", "Philadelphia Union": "PHI",
    "DC United": "DC", "Orlando City SC": "ORL",
    "FC Dallas": "DAL", "Houston Dynamo": "HOU",
    "Real Salt Lake": "RSL", "Sporting Kansas City": "SKC",
    "Chicago Fire": "CHI", "CF Montreal": "MTL",
    "Colorado Rapids": "COL", "San Jose Earthquakes": "SJ",
    "Minnesota United": "MIN", "Nashville SC": "NSH",
    "Charlotte FC": "CLT", "Austin": "ATX",
    "St Louis City": "STL", "St. Louis City": "STL",
    "New England Revolution": "NE",
}

_STRIP_PREFIXES = ("FC ", "AC ", "AS ", "SC ", "CF ", "RC ", "VfB ", "VfL ",
                    "TSG ", "RB ", "1. ", "1.", "FSV ", "SV ", "SG ")


def team_abbr(name: str | None) -> str:
    """3-letter team abbreviation. Uses manual map for known clubs, falls back
    to a heuristic for anything else (good enough for MLS reserve sides /
    cup minnows / new promoted clubs)."""
    if not name:
        return "—"
    name = str(name).strip()
    if not name:
        return "—"
    if name in TEAM_ABBR_OVERRIDES:
        return TEAM_ABBR_OVERRIDES[name]
    # Strip common prefixes
    s = name
    for pfx in _STRIP_PREFIXES:
        if s.startswith(pfx):
            s = s[len(pfx):]
            break
    words = [w for w in s.split() if w]
    if not words:
        return name[:3].upper()
    if len(words) == 1:
        return words[0][:3].upper()
    # Multi-word: first letter of each word, max 3 letters
    abbr = "".join(w[0] for w in words[:3]).upper()
    if len(abbr) < 3 and len(words[0]) >= 2:
        # Pad with extra letters from the first word so we always show 3 chars
        abbr = (abbr + words[0][1:])[:3].upper()
    return abbr


# ---------------------------------------------------------------------------
# Logos — vendored PNGs preferred, API-Sports CDN as fallback
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _logo_b64(team_id: int) -> str | None:
    """Read a vendored logo PNG and base64-encode it. Cached for the session."""
    p = LOGO_DIR / f"{int(team_id)}.png"
    if not p.exists():
        return None
    return base64.b64encode(p.read_bytes()).decode("ascii")


def team_logo_url(api_id: int | float | None) -> str | None:
    """Best URL for a team's logo. Prefers vendored PNG (data: URL), falls
    back to the API-Sports CDN if we don't have it on disk."""
    if api_id is None:
        return None
    try:
        if pd.isna(api_id):
            return None
        tid = int(api_id)
    except (TypeError, ValueError):
        return None
    b64 = _logo_b64(tid)
    if b64:
        return f"data:image/png;base64,{b64}"
    return f"https://media.api-sports.io/football/teams/{tid}.png"


def logo_img(api_id: int | float | None, width: int = 40) -> str:
    """HTML <img> tag for a team logo. Returns empty string if no id.

    Adds a 4-direction white drop-shadow so dark crests stay readable
    against the team-color tinted gradient header.
    """
    url = team_logo_url(api_id)
    if not url:
        return ""
    glow = (
        "filter:"
        " drop-shadow(1px 0 0 rgba(255,255,255,0.65))"
        " drop-shadow(-1px 0 0 rgba(255,255,255,0.65))"
        " drop-shadow(0 1px 0 rgba(255,255,255,0.65))"
        " drop-shadow(0 -1px 0 rgba(255,255,255,0.65));"
    )
    style = (
        f"width:{width}px;height:{width}px;object-fit:contain;"
        f"vertical-align:middle;{glow}"
    )
    return f'<img src="{url}" style="{style}" loading="lazy"/>'


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
def inject_global_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg-primary: #0E1117;
            --bg-secondary: #161B22;
            --bg-card: #11181F;
            --border: #1F2933;
            --text-primary: #F0F6FC;
            --text-secondary: #C9D1D9;
            --text-muted: #8B949E;
            --accent: #00C896;
            --green: #3FB950;
            --red: #F85149;
            --amber: #F0B93C;
        }

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

        .edge-pos { color: #3FB950; font-weight: 700; }
        .edge-neg { color: #F85149; }
        .calib-row { color: #8B949E; font-size: 0.85rem; margin-top: 0.3rem; font-style: italic; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Data loaders (cached)
# ---------------------------------------------------------------------------
def today_ct_date() -> _date:
    return datetime.now(CT).date()


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
def load_today_fixtures() -> pd.DataFrame:
    """Per-fixture metadata: API-FB team IDs, venue, city, round, status."""
    p = DATA_PROC / "today_fixtures.parquet"
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


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------
def calibrate_lookup(cal: pd.DataFrame, market: str, pct: float,
                       max_distance: int = 5) -> dict | None:
    """Calibration row for a given probability + market.

    Looks for the historical bucket nearest to the queried pct, but only
    returns a row if the bucket is within ``max_distance`` percentage points.
    This prevents misleading blurbs when the sim is at a probability the
    historical data has barely seen (e.g., asking for Over 3.5 at sim 85%
    when the table only has buckets up to ~45%, since real games almost
    never have such a high Over 3.5 prob).
    """
    if cal is None or cal.empty:
        return None
    sub = cal[cal["market"] == market]
    if sub.empty:
        return None
    target = int(round(pct * 100))
    if target in sub["pct"].values:
        return sub[sub["pct"] == target].iloc[0].to_dict()
    diff = (sub["pct"] - target).abs()
    nearest_idx = diff.idxmin()
    if int(diff.loc[nearest_idx]) > max_distance:
        return None
    return sub.loc[nearest_idx].to_dict()


def kalshi_implied(cents) -> float:
    if cents is None or pd.isna(cents):
        return float("nan")
    try:
        return float(cents) / 100.0
    except (TypeError, ValueError):
        return float("nan")


def cents_to_american(cents) -> str:
    """Cents (1-99) → American odds string. e.g. 45¢ → +122, 60¢ → -150."""
    if cents is None or pd.isna(cents):
        return "—"
    try:
        c = float(cents)
    except (TypeError, ValueError):
        return "—"
    if not (0 < c < 100):
        return "—"
    p = c / 100.0
    if p >= 0.5:
        return f"-{round(p / (1 - p) * 100)}"
    return f"+{round((1 - p) / p * 100)}"


def edge_html(edge: float) -> str:
    """Format an edge percentage as '+X.X% Edge' / '-X.X% Edge' with color."""
    if edge is None or pd.isna(edge):
        return ""
    if edge >= 0:
        return (f'<span class="edge-pos">+{edge*100:.1f}% '
                f'<span style="font-weight:600;letter-spacing:0.04em;">Edge</span></span>')
    return (f'<span class="edge-neg">{edge*100:.1f}% '
            f'<span style="font-weight:600;letter-spacing:0.04em;">Edge</span></span>')


def last_updated_text() -> str:
    dates = available_dates()
    if not dates:
        return "no data yet"
    latest = TODAY_DIR / dates[0]
    sim = latest / "sim_lines.parquet"
    if sim.exists():
        ts = datetime.fromtimestamp(sim.stat().st_mtime)
        return f"slate for {dates[0]} (refreshed {ts.strftime('%Y-%m-%d %H:%M')})"
    return f"slate for {dates[0]}"

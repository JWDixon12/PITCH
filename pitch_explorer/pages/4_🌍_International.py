"""International — upcoming national-team fixtures (next FIFA window + 2026 World Cup).

Reads data/processed/intl_upcoming.parquet (refreshed daily by
scrapers/fetch_intl_upcoming.py) and renders by date with comp grouping.

We don't sim international fixtures here — the player-aware club model can't
project intl XIs. This is a schedule view so users can see what's blocking
domestic football.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import CT, DATA_PROC, inject_global_css, today_ct_date


st.set_page_config(
    page_title="International · PITCH",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_css()


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_intl_upcoming() -> pd.DataFrame:
    p = DATA_PROC / "intl_upcoming.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    if df.empty:
        return df
    df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)
    df = df.sort_values("kickoff_utc").reset_index(drop=True)
    df["kickoff_ct"] = df["kickoff_utc"].dt.tz_convert(CT)
    df["date_ct"] = df["kickoff_ct"].dt.date
    return df


def fmt_kickoff(ts: pd.Timestamp) -> str:
    return ts.strftime("%I:%M %p CT").lstrip("0")


def date_header(d) -> str:
    today = today_ct_date()
    days_off = (d - today).days
    label = d.strftime("%A, %B %d, %Y").replace(" 0", " ")
    if days_off == 0:
        suffix = "Today"
    elif days_off == 1:
        suffix = "Tomorrow"
    elif 0 < days_off <= 6:
        suffix = f"in {days_off} days"
    elif days_off > 6:
        weeks = days_off // 7
        suffix = f"in {days_off} days" if weeks < 1 else f"in {weeks} week{'s' if weeks > 1 else ''}"
    else:
        suffix = ""
    return f"{label}" + (f"  ·  <span style='color:#8B949E;'>{suffix}</span>" if suffix else "")


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
df = load_intl_upcoming()

if df.empty:
    st.markdown(
        """<div class="hero">
        <div class="hero-title">🌍 International</div>
        <div class="hero-subtitle">No upcoming international fixtures cached yet.</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.info(
        "The intl scraper hasn't run yet for the current season. Once "
        "`scrapers/fetch_intl_upcoming.py` runs (it's part of the daily 5 AM CT "
        "refresh), this page will populate with the next FIFA window's "
        "fixtures plus the 2026 World Cup schedule."
    )
    st.stop()


# Filter to "future only" again — the parquet was correct at write time but
# the page may be loaded from cache after some matches have kicked off.
now_utc = datetime.now(timezone.utc)
df = df[df["kickoff_utc"] > now_utc].reset_index(drop=True)

if df.empty:
    st.markdown(
        """<div class="hero">
        <div class="hero-title">🌍 International</div>
        <div class="hero-subtitle">No upcoming international fixtures.</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.stop()


# ---------------------------------------------------------------------------
# Hero — break window summary
# ---------------------------------------------------------------------------
# "Next break window" = the cluster of consecutive (or near-consecutive) days
# starting from today/tomorrow. Heuristic: take everything within 14 days of
# the earliest upcoming date and call it the next window. Past that we're
# usually in domestic-league territory until the next FIFA break.
first_date = df["date_ct"].min()
window_end = first_date + timedelta(days=14)
near = df[df["date_ct"] <= window_end]
n_near = len(near)
n_total = len(df)
n_comps = df["comp_name"].nunique()

st.markdown(
    f"""<div class="hero">
    <div class="hero-title">🌍 International</div>
    <div class="hero-subtitle">{n_total} upcoming fixtures across {n_comps}
    competitions · next FIFA window opens {first_date.strftime('%b %d').replace(' 0', ' ')}
    with {n_near} matches in the next two weeks.</div>
    </div>""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Comp filter — popover with checkboxes (matches slate UX)
# ---------------------------------------------------------------------------
comps_present = sorted(df["comp_name"].unique())

def _ck_key(c: str) -> str:
    return f"intl_chk__{c}"

for c in comps_present:
    st.session_state.setdefault(_ck_key(c), True)

selected_comps = [c for c in comps_present if st.session_state[_ck_key(c)]]

if len(selected_comps) == len(comps_present):
    pop_label = f"All {len(comps_present)} competitions"
elif len(selected_comps) == 0:
    pop_label = "No competitions selected"
elif len(selected_comps) == 1:
    pop_label = f"1 competition: {selected_comps[0]}"
else:
    pop_label = f"{len(selected_comps)} of {len(comps_present)} competitions selected"

bar1, bar2 = st.columns([5, 5])
with bar1.popover(pop_label, use_container_width=True):
    bc1, bc2 = st.columns(2)
    if bc1.button("Select all", key="intl_select_all", use_container_width=True):
        for c in comps_present:
            st.session_state[_ck_key(c)] = True
        st.rerun()
    if bc2.button("Clear all", key="intl_clear_all", use_container_width=True):
        for c in comps_present:
            st.session_state[_ck_key(c)] = False
        st.rerun()
    st.divider()
    for c in comps_present:
        sub = df[df["comp_name"] == c]
        st.checkbox(f"{c}  ({len(sub)})", key=_ck_key(c))

# Range filter — Next 14 days / Next 30 days / All
range_choice = bar2.selectbox(
    "Range",
    ["Next 14 days", "Next 30 days", "All upcoming"],
    index=0,
)

if not selected_comps:
    st.warning("No competitions selected.")
    st.stop()

dfv = df[df["comp_name"].isin(selected_comps)]
if range_choice == "Next 14 days":
    cutoff = first_date + timedelta(days=14)
    dfv = dfv[dfv["date_ct"] <= cutoff]
elif range_choice == "Next 30 days":
    cutoff = first_date + timedelta(days=30)
    dfv = dfv[dfv["date_ct"] <= cutoff]

if dfv.empty:
    st.info("No fixtures in the selected range and competitions.")
    st.stop()


# ---------------------------------------------------------------------------
# Comp accents
# ---------------------------------------------------------------------------
COMP_COLOR = {
    "Friendlies": "#5865F2",
    "UEFA Nations League": "#001A4F",
    "World Cup": "#D4AF37",
}
COMP_TAG_BG = {
    "Friendlies": "rgba(88,101,242,0.18)",
    "UEFA Nations League": "rgba(0,26,79,0.45)",
    "World Cup": "rgba(212,175,55,0.16)",
}
COMP_TAG_FG = {
    "Friendlies": "#A5B0FF",
    "UEFA Nations League": "#8DA8FF",
    "World Cup": "#F0CC57",
}


def comp_pill(comp: str, rd: str = "") -> str:
    bg = COMP_TAG_BG.get(comp, "rgba(139,148,158,0.18)")
    fg = COMP_TAG_FG.get(comp, "#C9D1D9")
    txt = comp + (f" · {rd}" if rd else "")
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 10px;'
        f'border-radius:999px;font-size:11px;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.05em;">{txt}</span>'
    )


def flag_img(url: str | None, width: int = 36) -> str:
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


def fixture_row(r) -> str:
    home_logo = flag_img(r.get("home_logo"))
    away_logo = flag_img(r.get("away_logo"))
    home = r.get("home_name") or ""
    away = r.get("away_name") or ""
    rd = (r.get("round") or "").replace("Group Stage - ", "MD ")
    pill = comp_pill(r.get("comp_name") or "", rd)
    venue = r.get("venue_name") or ""
    city = r.get("venue_city") or ""
    venue_line = ""
    if venue or city:
        loc = " · ".join(x for x in [venue, city] if x)
        venue_line = (
            f'<div style="color:#8B949E;font-size:11px;margin-top:2px;">{loc}</div>'
        )
    kick = fmt_kickoff(r["kickoff_ct"])
    return f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
                padding:14px 18px;border-radius:12px;background:#11181F;
                border:1px solid #1F2933;margin-bottom:10px;">
      <div style="display:flex;align-items:center;gap:14px;flex:1;">
        <div style="display:flex;align-items:center;gap:10px;min-width:240px;">
          {home_logo}
          <span style="color:#F0F6FC;font-weight:600;font-size:14.5px;">{home}</span>
        </div>
        <span style="color:#8B949E;font-weight:600;">vs</span>
        <div style="display:flex;align-items:center;gap:10px;min-width:240px;">
          {away_logo}
          <span style="color:#F0F6FC;font-weight:600;font-size:14.5px;">{away}</span>
        </div>
      </div>
      <div style="text-align:right;">
        <div style="color:#E6EDF3;font-size:13.5px;font-weight:700;">{kick}</div>
        <div style="margin-top:4px;">{pill}</div>
        {venue_line}
      </div>
    </div>
    """


# ---------------------------------------------------------------------------
# Render — group by date
# ---------------------------------------------------------------------------
for d, group in dfv.groupby("date_ct", sort=True):
    st.markdown(
        f"""<div style="margin:1.4rem 0 0.6rem 0;
                       padding:8px 12px;border-left:3px solid #00C896;
                       background:rgba(0,200,150,0.06);
                       border-radius:0 8px 8px 0;">
            <div style="color:#F0F6FC;font-weight:700;font-size:15px;">
              {date_header(d)}
            </div>
            <div style="color:#8B949E;font-size:11.5px;margin-top:2px;
                        text-transform:uppercase;letter-spacing:0.06em;">
              {len(group)} match{'es' if len(group) != 1 else ''}
            </div>
           </div>""",
        unsafe_allow_html=True,
    )
    blocks = "".join(fixture_row(r) for _, r in group.iterrows())
    st.markdown(blocks, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """<div style="margin-top:2rem;padding:14px 18px;border-radius:12px;
        background:#161B22;border:1px solid #1F2933;color:#8B949E;
        font-size:12.5px;line-height:1.55;">
        <strong style="color:#C9D1D9;">Why no predictions on this page?</strong><br/>
        The player-aware club model is fit on club football — its player and
        manager-spell coefficients don't transfer cleanly to national teams,
        which assemble briefly and field very different XIs than club sides.
        We'll add a separate intl model trained on national-team data closer
        to the World Cup.
    </div>""",
    unsafe_allow_html=True,
)

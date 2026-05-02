"""Today's Slate — match cards with logos, win-prob bar, Kalshi market boxes."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import (
    CT, available_dates, calibrate_lookup, cents_to_american, edge_html,
    inject_global_css, league_color, league_label, kalshi_implied,
    load_calibration_btts, load_calibration_ml, load_calibration_total,
    load_kalshi, load_slate, load_today_fixtures, logo_img, team_abbr,
    today_ct_date,
)

st.set_page_config(
    page_title="Today's Slate · PITCH",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_global_css()

# ---- Hide the sidebar entirely + sticky top toolbar -------------------------
# The sticky CSS uses a hidden anchor div: we render <div class="pitch-toolbar-anchor">
# right before the columns row, then the CSS uses :has() to find the
# stElementContainer wrapping it and pins its NEXT sibling (the columns) to
# the top. This is robust against Streamlit re-renders because the sibling
# relationship is stable, unlike :first-of-type which depends on what other
# elements happen to be on the page.
st.markdown(
    """
    <style>
      /* Kill the sidebar and its toggle so the page is full-width */
      [data-testid="stSidebar"]            { display: none !important; }
      [data-testid="collapsedControl"]     { display: none !important; }
      [data-testid="stSidebarCollapsedControl"] { display: none !important; }

      /* Make Streamlit's own header transparent enough that our sticky toolbar
         meshes with it, and keep it on top of everything. */
      [data-testid="stHeader"] {
          background: rgba(14, 17, 23, 0.85) !important;
          backdrop-filter: blur(6px);
      }

      /* Hide the anchor element completely (it exists just as a CSS hook). */
      [data-testid="stElementContainer"]:has(.pitch-toolbar-anchor) {
          height: 0 !important;
          margin: 0 !important;
          padding: 0 !important;
          overflow: hidden !important;
      }

      /* Pin the columns row that comes right after the anchor.
         Sticky relative to its scrollable ancestor (Streamlit's main pane). */
      [data-testid="stElementContainer"]:has(.pitch-toolbar-anchor)
        + [data-testid="stHorizontalBlock"] {
          position: sticky !important;
          top: 3.25rem;
          z-index: 100;
          background: #0E1117;
          padding: 0.7rem 1rem 0.5rem 1rem;
          margin: 0 -1rem 1rem -1rem;
          border-bottom: 1px solid #1F2933;
          box-shadow: 0 4px 8px rgba(0,0,0,0.35);
      }
      /* Tighten widget labels in the toolbar */
      [data-testid="stElementContainer"]:has(.pitch-toolbar-anchor)
        + [data-testid="stHorizontalBlock"] label {
          font-size: 11px !important;
          color: #8B949E !important;
          text-transform: uppercase;
          letter-spacing: 0.06em;
      }

      /* Give the page a little extra top padding so the first content row isn't
         glued to the sticky toolbar's bottom border. */
      .block-container { padding-top: 1rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Top toolbar — Slate date + Leagues, frozen at the top
# ---------------------------------------------------------------------------
dates = available_dates()
default = today_ct_date().isoformat()
if default not in dates and dates:
    default = dates[0]
elif not dates:
    dates = [default]

# Anchor marker — used by CSS :has() to locate the columns row that follows.
st.markdown('<div class="pitch-toolbar-anchor"></div>', unsafe_allow_html=True)

# Two columns: date on the left, leagues filling the rest
tb_date, tb_leagues = st.columns([1, 3])
date_str = tb_date.selectbox(
    "Slate date", dates,
    index=dates.index(default) if default in dates else 0,
)

# Need to load the slate before we know which leagues to offer in the multiselect.
sim       = load_slate(date_str)
kalshi    = load_kalshi(date_str)
fixtures  = load_today_fixtures()
cal_ml    = load_calibration_ml()
cal_total = load_calibration_total()
cal_btts  = load_calibration_btts()

if sim.empty:
    tb_leagues.empty()
    st.warning(f"No matches in slate for {date_str}.")
    st.stop()

# Merge fixtures (logos, venue) and Kalshi *before* building the league list,
# so the multiselect reflects only leagues actually present today.
if not fixtures.empty:
    fix_cols = ["fixture_id", "home_api_id", "away_api_id",
                 "venue", "city", "round", "status"]
    have = [c for c in fix_cols if c in fixtures.columns]
    sim = sim.merge(fixtures[have], on="fixture_id", how="left")
if not kalshi.empty:
    sim = sim.merge(kalshi, on="fixture_id", how="left")

leagues_in_slate = sorted(sim["league_code"].unique())
selected = tb_leagues.multiselect(
    "Leagues", leagues_in_slate, default=leagues_in_slate,
    format_func=league_label,
    placeholder="Show all leagues",
)
sim = sim[sim["league_code"].isin(selected)] if selected else sim
sim = sim.sort_values("kickoff").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
n_total = len(sim)
n_with_market = int(sim["yes_home_cents"].notna().sum()) if "yes_home_cents" in sim.columns else 0
n_leagues = sim["league_code"].nunique()

st.markdown(
    f"""<div class="hero">
    <div class="hero-title">⚽ Today's Slate</div>
    <div class="hero-subtitle">{date_str} — {n_total} matches across {n_leagues} leagues, """
    f"""{n_with_market} with live Kalshi markets.</div>
    </div>""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------
GREEN = "#3FB950"
RED   = "#F85149"
GRAY  = "#8B949E"
DRAW  = "#F0B93C"


def fmt_kickoff(ts) -> str:
    """Local-CT kickoff string. Uses the fixed-offset CT we set in utils."""
    if ts is None or pd.isna(ts):
        return "TBD"
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    try:
        local = t.astimezone(CT)
    except Exception:
        local = t
    return local.strftime("%a %b %d  %I:%M %p CT").lstrip("0")


def fmt_status(s) -> str:
    if s is None or pd.isna(s):
        return ""
    s = str(s)
    if s in ("FT", "AET", "PEN"):
        return f'<span style="color:#3FB950;font-weight:600;">FINAL</span>'
    if s in ("1H", "2H", "HT", "ET", "BT", "P"):
        return f'<span style="color:#F0B93C;font-weight:600;">LIVE · {s}</span>'
    if s == "NS":
        return ""
    if s in ("PST", "CANC", "ABD", "AWD", "WO", "TBD"):
        return f'<span style="color:#F85149;font-weight:600;">{s}</span>'
    return f'<span style="color:#8B949E;">{s}</span>'


def game_header(r: pd.Series) -> str:
    lg = r["league_code"]
    accent = league_color(lg)
    home = r["home"]; away = r["away"]
    venue = r.get("venue") or ""
    city  = r.get("city") or ""
    rnd   = r.get("round") or ""
    home_logo = logo_img(r.get("home_api_id"), width=44)
    away_logo = logo_img(r.get("away_api_id"), width=44)

    venue_line_parts = []
    if venue:
        venue_line_parts.append(venue)
    if city and city not in venue:
        venue_line_parts.append(city)
    if rnd:
        venue_line_parts.append(rnd)
    venue_line = " · ".join(venue_line_parts)

    status_html = fmt_status(r.get("status"))
    status_part = f' &nbsp;·&nbsp; {status_html}' if status_html else ""

    # Logos sit immediately to the left of each team name, mirroring the
    # MLB layout: "[logo] HOME  vs  [logo] AWAY"
    return (
        f'<div style="border-radius:14px;overflow:hidden;margin-top:18px;'
        f'background:linear-gradient(90deg,{accent}40 0%,#1C2128 50%,{accent}40 100%);'
        f'border:1px solid #2D333B;">'
        f'<div style="padding:18px 24px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'flex-wrap:wrap;gap:12px;">'
        # Left: [logo] HOME vs [logo] AWAY
        f'<div style="font-size:22px;font-weight:700;color:#F0F6FC;">'
        f'{home_logo} <span style="margin:0 6px;">{home}</span>'
        f'<span style="color:#8B949E;font-weight:400;margin:0 6px;">vs</span>'
        f'{away_logo} <span style="margin:0 6px;">{away}</span>'
        f'</div>'
        # Right: time, league, status
        f'<div style="text-align:right;">'
        f'<div style="font-size:14px;color:#C9D1D9;font-weight:600;">'
        f'{fmt_kickoff(r["kickoff"])}</div>'
        + (f'<div style="font-size:12px;margin-top:2px;">{status_html}</div>'
            if status_html else "")
        + f'<div style="font-size:11px;color:#8B949E;margin-top:2px;">{league_label(lg)}</div>'
        f'</div>'
        f'</div>'
        + (f'<div style="margin-top:10px;font-size:12px;color:#8B949E;">'
            f'🏟️ {venue_line}</div>'
            if venue_line else "")
        + f'</div></div>'
    )


def _cal_inline(label: str, cal: dict | None) -> str:
    """Compact one-fragment calibration string for the win-prob bar footer.
    Returns '' when there's no usable bucket — caller filters those out.
    Format: 'Home 62% → 142-79 (64.3%)'
    """
    if not cal or int(cal.get("n_games", 0)) < 10:
        return ""
    return (
        f'<span title="From the 13.7K-match historical calibration table, '
        f'over {int(cal["n_games"]):,} comparable games.">'
        f'<span style="color:#C9D1D9;">{label}</span> '
        f'{int(cal["pct"])}% &rarr; <b style="color:#C9D1D9;">'
        f'{int(cal["wins"])}-{int(cal["losses"])} '
        f'({cal["actual_rate"]*100:.1f}%)</b></span>'
    )


def _flip_cal(cal: dict | None) -> dict | None:
    """Calibration when looking at the OTHER side of a YES/NO market.
    Sim 60% over → sim 40% under, the bucket's wins/losses flip."""
    if not cal:
        return None
    return {
        "pct":        100 - int(cal["pct"]),
        "n_games":    int(cal["n_games"]),
        "wins":       int(cal["losses"]),  # other side's "wins" are this side's "losses"
        "losses":     int(cal["wins"]),
        "actual_rate": 1.0 - float(cal["actual_rate"]),
    }


def winprob_bar(r: pd.Series) -> str:
    """Three-segment H / D / A win-probability bar + per-side calibration blurbs."""
    p_h = float(r["p_home_win"])
    p_d = float(r["p_draw"])
    p_a = float(r["p_away_win"])
    home = r["home"]; away = r["away"]

    # Color the favored side green, the underdog red, draw amber.
    if abs(p_h - p_a) < 0.005:
        home_color = away_color = GRAY
    elif p_h > p_a:
        home_color, away_color = GREEN, RED
    else:
        home_color, away_color = RED, GREEN

    h_pct = p_h * 100; d_pct = p_d * 100; a_pct = p_a * 100
    most_likely = r.get("most_likely_score") or "—"
    eg_h = r.get("lambda_home"); eg_a = r.get("lambda_away")
    eg_total = r.get("expected_total_goals")
    n_sims = int(r.get("n_sims") or 0)
    top3 = r.get("top3_scores") or ""

    # "Projected: HOME 1.95 — 1.20 AWAY · Total 3.15 · most likely 2-1 · 10K sims"
    parts = []
    if (eg_h is not None and pd.notna(eg_h)
        and eg_a is not None and pd.notna(eg_a)):
        parts.append(
            f'<span title="Expected goals from sim (lambda_home / lambda_away)">'
            f'Projected: <b style="color:#C9D1D9;">{home} {float(eg_h):.2f}</b> — '
            f'<b style="color:#C9D1D9;">{float(eg_a):.2f} {away}</b></span>'
        )
    if eg_total is not None and pd.notna(eg_total):
        parts.append(f'Total <b style="color:#C9D1D9;">{float(eg_total):.2f}</b>')
    if most_likely and most_likely != "—":
        ml_title = f'Top 3 scorelines: {top3}' if top3 else most_likely
        # "VIL 2 - 0 LEV" style — pad spaces around the score for readability
        score_str = str(most_likely).replace("-", " - ")
        ml_label  = f"{team_abbr(home)} {score_str} {team_abbr(away)}"
        parts.append(
            f'Most likely <b style="color:#C9D1D9;" '
            f'title="{ml_title}">{ml_label}</b>'
        )
    parts.append(f'<span style="font-style:italic;color:#586069;">'
                 f'{n_sims:,} sims</span>')
    projected_line = " &nbsp;·&nbsp; ".join(parts)

    # Calibration: compact one-line "Home 62% → 142-79 (64.3%)  ·  Draw 22% → ..." footer
    cal_h = calibrate_lookup(cal_ml, "ML_home", p_h)
    cal_d = calibrate_lookup(cal_ml, "Draw",    p_d)
    cal_a = calibrate_lookup(cal_ml, "ML_away", p_a)
    cal_parts = [s for s in [
        _cal_inline(home, cal_h),
        _cal_inline("Draw", cal_d),
        _cal_inline(away, cal_a),
    ] if s]
    cal_block = ""
    if cal_parts:
        cal_block = (
            f'<div style="text-align:center;font-size:13px;color:#8B949E;'
            f'margin-top:14px;padding-top:12px;border-top:1px solid #21262D;'
            f'line-height:1.55;">'
            + " &nbsp;·&nbsp; ".join(cal_parts)
            + f' <span style="color:#586069;font-size:12px;">(historical hit rate)</span>'
            + f'</div>'
        )

    # The "Draw X%" label has to land under the *center* of the yellow draw
    # segment, which lives between the home (h_pct%) and away (a_pct%) segments
    # of the bar. Center of draw segment = h_pct + d_pct/2, expressed as a
    # percent of the bar's width. We absolutely position the label inside a
    # relative-positioned bar wrapper, so it tracks the draw segment exactly
    # regardless of the surrounding flex widths.
    draw_center_pct = h_pct + d_pct / 2.0

    return (
        f'<div style="padding:14px 18px 18px 18px;background:#0E1117;'
        f'border:1px solid #2D333B;border-radius:8px;margin-top:8px;">'
        # Top: team labels with % + the bar between them
        f'<div style="display:flex;align-items:center;gap:14px;">'
        f'<div style="font-size:15px;font-weight:700;color:{home_color};'
        f'min-width:140px;text-align:right;">'
        f'{home} <span style="color:#C9D1D9;font-weight:700;">{h_pct:.0f}%</span>'
        f'</div>'
        # Bar wrapper (relative) -> bar + absolutely-positioned Draw label
        f'<div style="flex:1;position:relative;padding-bottom:24px;">'
        f'<div style="height:14px;border-radius:7px;background:#21262D;'
        f'overflow:hidden;display:flex;">'
        f'<div style="width:{h_pct:.2f}%;background:{home_color};"></div>'
        f'<div style="width:{d_pct:.2f}%;background:{DRAW};"></div>'
        f'<div style="width:{a_pct:.2f}%;background:{away_color};"></div>'
        f'</div>'
        # Draw % anchored to the center of the yellow segment
        f'<div style="position:absolute;top:18px;left:{draw_center_pct:.2f}%;'
        f'transform:translateX(-50%);font-size:13px;color:{DRAW};'
        f'font-weight:700;white-space:nowrap;">'
        f'Draw {d_pct:.0f}%'
        f'</div>'
        f'</div>'
        f'<div style="font-size:15px;font-weight:700;color:{away_color};'
        f'min-width:140px;text-align:left;">'
        f'<span style="color:#C9D1D9;font-weight:700;">{a_pct:.0f}%</span> {away}'
        f'</div>'
        f'</div>'
        # MLB-style projected line: "Projected: HOME 1.95 — 1.20 AWAY · Total 3.15 · ..."
        f'<div style="text-align:center;font-size:15px;color:#C9D1D9;'
        f'margin-top:18px;line-height:1.55;">'
        f'{projected_line}'
        f'</div>'
        + cal_block
        + f'</div>'
    )


def _mini_cal_pill(cal: dict | None,
                    yes_word: str = "hits", no_word: str = "misses") -> str:
    """Calibration blurb sized for the totals/props tiles.

    Reads as a sentence: "When the sim says 82%, this has gone 3,474-771 (81.8%)
    over 4,245 games."
    """
    if not cal or int(cal.get("n_games", 0)) < 10:
        return ""
    return (
        f'<div style="font-size:13px;color:#8B949E;line-height:1.5;'
        f'margin-top:12px;text-align:center;" '
        f'title="Historical calibration, ±2.5% local window across the 13.7K-match backtest.">'
        f'When the sim says <b style="color:#C9D1D9;">{int(cal["pct"])}%</b>, '
        f'this has gone <b style="color:#F0F6FC;">'
        f'{int(cal["wins"]):,}-{int(cal["losses"]):,} '
        f'({cal["actual_rate"]*100:.1f}%)</b><br/>'
        f'over <b style="color:#C9D1D9;">{int(cal["n_games"]):,}</b> games'
        f'</div>'
    )


def secondary_markets(r: pd.Series) -> str:
    """Totals + BTTS + clean-sheet probabilities row, each with calibration."""
    p_o15 = float(r.get("p_o_15") or 0)
    p_o25 = float(r.get("p_o_25") or 0)
    p_o35 = float(r.get("p_o_35") or 0)
    p_btts = float(r.get("p_btts") or 0)
    p_cs_h = float(r.get("p_cs_home") or 0)
    p_cs_a = float(r.get("p_cs_away") or 0)
    eg_total = float(r.get("expected_total_goals") or 0)

    cal_o15_d  = calibrate_lookup(cal_total, "Over_1.5", p_o15)
    cal_o25_d  = calibrate_lookup(cal_total, "Over_2.5", p_o25)
    cal_o35_d  = calibrate_lookup(cal_total, "Over_3.5", p_o35)
    cal_u25_d  = _flip_cal(cal_o25_d)  # Under 2.5 = inverse of Over 2.5
    cal_btts_d = calibrate_lookup(cal_btts, "BTTS", p_btts)

    def cell(label: str, value_pct: float, cal: dict | None,
              hint: str = "") -> str:
        cal_html = _mini_cal_pill(cal)
        return (
            f'<div style="flex:1 1 220px;min-width:220px;min-height:180px;'
            f'padding:18px 16px;background:#161B22;border:1px solid #2D333B;'
            f'border-radius:10px;text-align:center;display:flex;'
            f'flex-direction:column;align-items:center;">'
            f'<div style="font-size:13px;color:#8B949E;text-transform:uppercase;'
            f'letter-spacing:0.08em;font-weight:600;">'
            f'{label}</div>'
            f'<div style="font-size:40px;font-weight:800;color:#F0F6FC;'
            f'margin-top:6px;line-height:1.1;">'
            f'{value_pct*100:.0f}%</div>'
            + (f'<div style="font-size:12px;color:#586069;margin-top:3px;">'
                f'{hint}</div>' if hint else "")
            + cal_html
            + f'</div>'
        )

    def plain_cell(label: str, value_pct: float, hint: str = "") -> str:
        return (
            f'<div style="flex:1 1 220px;min-width:220px;min-height:180px;'
            f'padding:18px 16px;background:#161B22;border:1px solid #2D333B;'
            f'border-radius:10px;text-align:center;display:flex;'
            f'flex-direction:column;align-items:center;justify-content:center;">'
            f'<div style="font-size:13px;color:#8B949E;text-transform:uppercase;'
            f'letter-spacing:0.08em;font-weight:600;">'
            f'{label}</div>'
            f'<div style="font-size:40px;font-weight:800;color:#F0F6FC;'
            f'margin-top:6px;line-height:1.1;">'
            f'{value_pct*100:.0f}%</div>'
            + (f'<div style="font-size:12px;color:#586069;margin-top:3px;">'
                f'{hint}</div>' if hint else "")
            + f'</div>'
        )

    return (
        f'<div style="margin-top:8px;padding:10px 14px;background:#0E1117;'
        f'border:1px solid #2D333B;border-radius:8px;">'
        f'<div style="font-size:11px;color:#8B949E;text-transform:uppercase;'
        f'letter-spacing:0.06em;margin-bottom:8px;">Totals & props</div>'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;">'
        + cell("Over 1.5",  p_o15,         cal_o15_d)
        + cell("Over 2.5",  p_o25,         cal_o25_d, f"EG {eg_total:.2f}")
        + cell("Under 2.5", 1.0 - p_o25,   cal_u25_d)
        + cell("Over 3.5",  p_o35,         cal_o35_d)
        + cell("BTTS yes",  p_btts,        cal_btts_d)
        + plain_cell("Home CS", p_cs_h, "clean sheet")
        + plain_cell("Away CS", p_cs_a, "clean sheet")
        + f'</div></div>'
    )


def _cal_blurb(cal: dict | None, label_yes: str = "wins",
                label_no: str = "losses") -> str:
    if not cal:
        return ""
    return (
        f'<div style="color:#8B949E;font-size:12px;margin-top:6px;line-height:1.45;" '
        f'title="From the 13.7K-match calibration table, ±2.5% local window.">'
        f'When the sim says <b style="color:#C9D1D9;">{int(cal["pct"])}%</b>, '
        f'this has gone <b style="color:#F0F6FC;">'
        f'{int(cal["wins"]):,}-{int(cal["losses"]):,} '
        f'({cal["actual_rate"]*100:.1f}%)</b> over '
        f'<b style="color:#C9D1D9;">{int(cal["n_games"]):,}</b> games'
        f'</div>'
    )


def kalshi_panel(r: pd.Series) -> str:
    """Kalshi market boxes — H/D/A + Over (line) + BTTS — with sim/edge/cal."""
    yes_h = r.get("yes_home_cents")
    yes_d = r.get("yes_draw_cents")
    yes_a = r.get("yes_away_cents")
    yes_o = r.get("yes_over_cents")
    yes_u = r.get("yes_under_cents")
    yes_b = r.get("yes_btts_cents")
    line  = r.get("total_line")

    if not any(pd.notna(x) for x in [yes_h, yes_d, yes_a, yes_o, yes_u, yes_b]):
        return (
            '<div style="margin-top:8px;padding:10px 14px;background:#0E1117;'
            'border:1px solid #2D333B;border-radius:8px;color:#8B949E;'
            'font-size:12px;text-align:center;">'
            'Kalshi markets unavailable for this match'
            '</div>'
        )

    p_h = float(r["p_home_win"]); p_d = float(r["p_draw"]); p_a = float(r["p_away_win"])
    p_o25 = float(r.get("p_o_25") or 0)
    p_btts = float(r.get("p_btts") or 0)

    def market_cell(label: str, cents, sim_p: float, color: str,
                     cal_market: str | None = None,
                     cal_table: pd.DataFrame | None = None,
                     flip_cal_market: str | None = None,
                     flip_cal_table: pd.DataFrame | None = None) -> str:
        cents_v = kalshi_implied(cents)
        if not np.isfinite(cents_v):
            return ""
        american = cents_to_american(cents)
        edge = sim_p - cents_v
        edge_pill = edge_html(edge)

        cal_html = ""
        cal = None
        if cal_market and cal_table is not None and not cal_table.empty:
            cal = calibrate_lookup(cal_table, cal_market, sim_p)
        elif flip_cal_market and flip_cal_table is not None and not flip_cal_table.empty:
            # Look up the OPPOSITE side of a YES/NO market and flip wins/losses
            cal_other = calibrate_lookup(flip_cal_table, flip_cal_market, 1.0 - sim_p)
            cal = _flip_cal(cal_other)
        if cal and int(cal.get("n_games", 0)) >= 10:
            cal_html = _cal_blurb(cal)

        return (
            f'<div style="flex:1;min-width:140px;padding:10px;background:#161B22;'
            f'border:1px solid #2D333B;border-radius:8px;">'
            f'<div style="font-size:10px;color:#8B949E;text-transform:uppercase;letter-spacing:0.06em;">'
            f'{label}</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px;margin-top:2px;">'
            f'<div style="font-size:22px;font-weight:700;color:{color};">{american}</div>'
            f'<div style="font-size:11px;color:#8B949E;">{int(round(cents_v*100))}¢</div>'
            f'</div>'
            f'<div style="font-size:11px;color:#C9D1D9;margin-top:4px;">'
            f'<span title="Kalshi YES implied probability">Kalshi {cents_v*100:.0f}%</span>'
            f' · <span title="Our sim\'s probability">Sim {sim_p*100:.0f}%</span>'
            f' · {edge_pill}'
            f'</div>'
            f'{cal_html}'
            f'</div>'
        )

    cells = []
    if pd.notna(yes_h):
        cells.append(market_cell(f"{r['home']} ML", yes_h, p_h, "#58A6FF",
                                  "ML_home", cal_ml))
    if pd.notna(yes_d):
        cells.append(market_cell("Draw", yes_d, p_d, DRAW,
                                  "Draw", cal_ml))
    if pd.notna(yes_a):
        cells.append(market_cell(f"{r['away']} ML", yes_a, p_a, "#FF7B72",
                                  "ML_away", cal_ml))
    # Total — only render if line is 2.5 (we calibrate against p_o_25 directly)
    if pd.notna(line) and float(line) == 2.5:
        if pd.notna(yes_o):
            cells.append(market_cell(f"Over {line}", yes_o, p_o25, GREEN,
                                      "Over_2.5", cal_total))
        if pd.notna(yes_u):
            cells.append(market_cell(f"Under {line}", yes_u, 1.0 - p_o25, RED,
                                      None, None,
                                      flip_cal_market="Over_2.5",
                                      flip_cal_table=cal_total))
    if pd.notna(yes_b):
        cells.append(market_cell("BTTS yes", yes_b, p_btts, "#A371F7",
                                  "BTTS", cal_btts))

    body = "".join(cells)
    return (
        f'<div style="margin-top:8px;padding:12px 14px;background:#0E1117;'
        f'border:1px solid #2D333B;border-radius:8px;">'
        f'<div style="font-size:11px;color:#8B949E;text-transform:uppercase;'
        f'letter-spacing:0.06em;margin-bottom:8px;">Kalshi markets</div>'
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;">{body}</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Render — bold divider between games
# ---------------------------------------------------------------------------
GAME_DIVIDER = (
    '<div style="margin:42px 0 0 0;height:0;'
    'border-top:3px solid #30363D;'
    'box-shadow:0 1px 0 #1F2933;"></div>'
)

for i, (_, row) in enumerate(sim.iterrows()):
    if i > 0:
        st.markdown(GAME_DIVIDER, unsafe_allow_html=True)
    st.markdown(game_header(row), unsafe_allow_html=True)
    st.markdown(winprob_bar(row),  unsafe_allow_html=True)
    st.markdown(secondary_markets(row), unsafe_allow_html=True)
    st.markdown(kalshi_panel(row),   unsafe_allow_html=True)

st.divider()
st.caption(
    "Edges shown are simulator probability minus Kalshi implied probability. "
    "Positive = sim says more likely than market. "
    "Calibration blurbs draw on a 13,708-match historical backtest. "
    "PITCH is research; not betting advice."
)

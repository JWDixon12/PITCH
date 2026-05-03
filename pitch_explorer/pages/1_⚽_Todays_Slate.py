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
    load_kalshi, load_slate, load_today_fixtures, logo_img, sim_run_at_ct,
    team_abbr, today_ct_date,
)

st.set_page_config(
    page_title="Today's Slate · PITCH",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_css()

# ---- Top toolbar (no sticky — that broke page scrolling) --------------------
# Earlier versions used `position: sticky` plus `overflow: visible !important`
# on `[data-testid="stMain"]`, but stMain IS the main scroll container — making
# it overflow:visible removed the page scrollbar entirely. The toolbar now just
# scrolls with the page; the sidebar still holds nav links and the date is the
# first thing on screen, so this is a small UX cost vs. a broken page.
st.markdown(
    """
    <style>
      /* Translucent Streamlit header — visual continuity with the toolbar */
      [data-testid="stHeader"] {
          background: rgba(14, 17, 23, 0.85) !important;
          backdrop-filter: blur(6px);
          z-index: 99 !important;
      }

      /* Hide the anchor element (CSS hook only) */
      [data-testid="stElementContainer"]:has(.pitch-toolbar-anchor) {
          height: 0 !important;
          margin: 0 !important;
          padding: 0 !important;
          overflow: hidden !important;
      }

      /* Style the columns row that sits right after the anchor */
      [data-testid="stElementContainer"]:has(.pitch-toolbar-anchor)
        + [data-testid="stHorizontalBlock"] {
          background: #0E1117;
          padding: 14px 1rem 12px 1rem !important;
          margin: 0 -1rem 1rem -1rem !important;
          border-bottom: 2px solid #1F2933;
          box-shadow: 0 4px 12px rgba(0,0,0,0.4);
      }

      /* Tighten widget labels in the toolbar */
      [data-testid="stElementContainer"]:has(.pitch-toolbar-anchor)
        + [data-testid="stHorizontalBlock"] label {
          font-size: 11px !important;
          color: #8B949E !important;
          text-transform: uppercase;
          letter-spacing: 0.06em;
      }

      .block-container { padding-top: 1rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Top toolbar — Slate date + Leagues + page nav, frozen at the top
# ---------------------------------------------------------------------------
dates = available_dates()
default = today_ct_date().isoformat()
if default not in dates and dates:
    default = dates[0]
elif not dates:
    dates = [default]

# Anchor marker — used by CSS :has() to locate the columns row that follows.
st.markdown('<div class="pitch-toolbar-anchor"></div>', unsafe_allow_html=True)

# Date | Leagues | nav links
tb_date, tb_leagues, tb_nav = st.columns([2, 5, 2])
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

# Last-simulated timestamp in CT — shows when sim_lines.parquet was last written
with tb_nav:
    sim_at = sim_run_at_ct(date_str)
    if sim_at:
        st.markdown(
            f"""
            <div style="text-align:right; padding-top:4px;">
              <div style="font-size:11px; color:#8B949E; text-transform:uppercase;
                          letter-spacing:0.06em;">Last simulated</div>
              <div style="font-size:13px; color:#E6EDF3; font-weight:600;
                          margin-top:2px;">{sim_at}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


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


def _s(v) -> str:
    """NaN-safe stringify — pandas NaN is truthy under bool(), so `x or ''`
    leaves NaN through and `in` checks downstream blow up."""
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    return str(v)


def _sim_status_pill(status: str) -> str:
    """PRELIMINARY (amber) before XI confirmation, FINAL (green) once both
    sides' lineups are confirmed by API-Football. Empty when missing.

    Tooltip explains the meaning so users hovering the pill understand why
    a 9 AM-CT view shows mostly preliminary and a noon-CT view shows mostly
    final for European matches.
    """
    s = (str(status) if status else "").lower()
    if s == "final":
        bg, fg, label = "#1F4D2A", "#7EE787", "FINAL SIM"
        tip = "Both starting XIs confirmed by API-Football — this sim uses the actual players starting today."
    elif s == "preliminary":
        bg, fg, label = "#4D3A1F", "#F0B93C", "PRELIMINARY"
        tip = "At least one side's starting XI not yet confirmed. Sim used the projected XI from the last 5 matches and will be re-run automatically once lineups land."
    else:
        return ""
    return (
        f'<span title="{tip}" style="display:inline-block;padding:3px 9px;'
        f'border-radius:10px;background:{bg};color:{fg};'
        f'font-size:10px;font-weight:700;letter-spacing:0.06em;'
        f'margin-top:4px;">{label}</span>'
    )


def game_header(r: pd.Series) -> str:
    lg = r["league_code"]
    accent = league_color(lg)
    home = r["home"]; away = r["away"]
    venue = _s(r.get("venue"))
    city  = _s(r.get("city"))
    rnd   = _s(r.get("round"))
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
    sim_status_html = _sim_status_pill(_s(r.get("sim_status")))

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
        # Right: time, league, status, sim_status pill
        f'<div style="text-align:right;">'
        f'<div style="font-size:14px;color:#C9D1D9;font-weight:600;">'
        f'{fmt_kickoff(r["kickoff"])}</div>'
        + (f'<div style="font-size:12px;margin-top:2px;">{status_html}</div>'
            if status_html else "")
        + f'<div style="font-size:11px;color:#8B949E;margin-top:2px;">{league_label(lg)}</div>'
        + (f'<div>{sim_status_html}</div>' if sim_status_html else "")
        + f'</div>'
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
    # Parse top3_scores ("1-1 (12.3%) | 1-0 (10.4%) | 2-1 (8.7%)") into 3 cells
    # we'll render with EQUAL visual weight. The Poisson modal collapses 60%+ of
    # EPL fixtures to "1-1" because Poisson with lambda in (1,2) has mode 1 — but
    # in reality 1-1 only happens 11% of the time. Anointing the top cell as
    # "Most likely" overstates a 12% probability, so we show the top-3 cluster
    # as a band of equally-weighted pills instead.
    top_entries: list[str] = []
    if top3:
        for chunk in [s.strip() for s in str(top3).split("|") if s.strip()]:
            top_entries.append(chunk)

    parts.append(f'<span style="font-style:italic;color:#586069;">'
                 f'{n_sims:,} sims</span>')
    projected_line = " &nbsp;·&nbsp; ".join(parts)

    # Score-range band — three top scores, equal weight, no "most likely" winner
    score_range_html = ""
    if top_entries:
        pills = []
        for entry in top_entries[:3]:
            if "(" in entry and "%)" in entry:
                raw_score = entry.split("(")[0].strip()
                pct = entry[entry.find("(")+1:entry.find("%)")] + "%"
                score_str = raw_score.replace("-", " - ")
                label = f"{team_abbr(home)} {score_str} {team_abbr(away)}"
                pills.append(
                    f'<span style="display:inline-block;padding:8px 14px;'
                    f'border:1px solid #2D333B;border-radius:8px;'
                    f'background:#161B22;font-size:14px;color:#C9D1D9;'
                    f'margin:0 6px;font-weight:600;">'
                    f'{label} <span style="color:#8B949E;font-weight:500;'
                    f'margin-left:4px;">{pct}</span>'
                    f'</span>'
                )
        if pills:
            score_range_html = (
                f'<div style="text-align:center;margin-top:14px;'
                f'font-size:11px;color:#8B949E;text-transform:uppercase;'
                f'letter-spacing:0.08em;font-weight:600;">Score range</div>'
                f'<div style="text-align:center;margin-top:8px;line-height:2.2;">'
                + "".join(pills)
                + '</div>'
            )

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
        + score_range_html
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


def _drivers_block(team: str, drivers: str) -> str:
    """Top-3 attack drivers, rendered as small chips. Empty string if no data.

    Coefs near zero (|c| < 0.005) get clamped to +0.00 so we don't render
    the misleading '-0.00' that the model's `{c:+.02f}` formatter produces
    for tiny-negative coefficients. Color flips red when the player's coef
    is meaningfully negative (i.e., they suppress goals when they start).
    """
    if not drivers or pd.isna(drivers):
        return ""
    chips: list[str] = []
    for chunk in [s.strip() for s in str(drivers).split(",") if s.strip()]:
        # Each chunk looks like "Caicedo (+0.34)"
        if "(" in chunk and chunk.endswith(")"):
            name = chunk[:chunk.rfind("(")].strip()
            coef_str = chunk[chunk.rfind("(") + 1:-1]
        else:
            name, coef_str = chunk, ""

        coef_html = ""
        if coef_str:
            try:
                coef_val = float(coef_str)
            except ValueError:
                coef_val = 0.0
            if abs(coef_val) < 0.005:
                display = "+0.00"
                color = "#8B949E"
            elif coef_val > 0:
                display = f"+{coef_val:.2f}"
                color = "#7EE787"
            else:
                display = f"{coef_val:.2f}"
                color = "#F85149"
            coef_html = (f' <span style="color:{color};font-weight:500;'
                         f'margin-left:4px;">{display}</span>')

        chips.append(
            f'<span style="display:inline-block;padding:5px 10px;'
            f'background:#161B22;border:1px solid #2D333B;border-radius:8px;'
            f'font-size:12px;color:#C9D1D9;margin:3px 4px 0 0;">'
            f'{name}{coef_html}</span>'
        )
    if not chips:
        return ""
    return (
        f'<div style="margin-top:8px;">'
        f'<div style="font-size:11px;color:#8B949E;text-transform:uppercase;'
        f'letter-spacing:0.06em;font-weight:600;">Top drivers · {team}</div>'
        f'<div style="margin-top:4px;">' + "".join(chips) + '</div>'
        f'</div>'
    )


def _rotation_alert_block(rot: int | float | None) -> str:
    """Inline alert when ≥3 usual starters are missing from a confirmed XI."""
    try:
        n = int(rot) if rot is not None and not pd.isna(rot) else 0
    except (TypeError, ValueError):
        n = 0
    if n < 3:
        return ""
    return (
        f'<div style="margin-top:6px;padding:4px 10px;background:#4D1F1F;'
        f'border-radius:6px;color:#F85149;font-size:12px;font-weight:600;'
        f'display:inline-block;">'
        f'⚠️ Rotation alert · {n} usual starters out</div>'
    )


def lineup_panel(r: pd.Series) -> str:
    """Side-by-side top-drivers panel — only renders when PA columns exist.

    Renders the per-player attack-coefficient chips that explain *why* the
    sim landed where it did. Returns '' when the row is from the legacy
    team-only sim (no driver columns), so old slates still work unchanged.

    Rotation alert appears inline when ≥3 of the team's usual starters are
    missing from a confirmed XI — a real signal that a result might surprise.
    """
    if "home_top_drivers" not in r.index and "home_xi_source" not in r.index:
        return ""

    h_drv = _s(r.get("home_top_drivers"))
    a_drv = _s(r.get("away_top_drivers"))
    h_rot = r.get("home_rotation_alert")
    a_rot = r.get("away_rotation_alert")

    if not (h_drv or a_drv):
        return ""

    home = r["home"]; away = r["away"]

    def side(team: str, drv: str, rot) -> str:
        return (
            f'<div style="flex:1 1 320px;min-width:280px;padding:16px 18px;'
            f'background:#161B22;border:1px solid #2D333B;border-radius:10px;">'
            f'<div style="font-size:14px;font-weight:700;color:#F0F6FC;">'
            f'{team}</div>'
            f'{_rotation_alert_block(rot)}'
            f'{_drivers_block(team, drv)}'
            f'</div>'
        )

    return (
        f'<div style="margin-top:8px;padding:14px 16px;background:#0E1117;'
        f'border:1px solid #2D333B;border-radius:10px;">'
        f'<div style="font-size:11px;color:#8B949E;text-transform:uppercase;'
        f'letter-spacing:0.06em;margin-bottom:10px;">Top drivers</div>'
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;">'
        + side(home, h_drv, h_rot)
        + side(away, a_drv, a_rot)
        + f'</div></div>'
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
            f'<div style="flex:1 1 220px;min-width:220px;min-height:180px;'
            f'padding:18px 16px;background:#161B22;border:1px solid #2D333B;'
            f'border-radius:10px;display:flex;flex-direction:column;">'
            f'<div style="font-size:13px;color:#8B949E;text-transform:uppercase;'
            f'letter-spacing:0.08em;font-weight:600;">'
            f'{label}</div>'
            f'<div style="display:flex;align-items:baseline;gap:10px;margin-top:6px;">'
            f'<div style="font-size:34px;font-weight:800;color:{color};line-height:1;">'
            f'{american}</div>'
            f'<div style="font-size:14px;color:#8B949E;">{int(round(cents_v*100))}¢</div>'
            f'</div>'
            f'<div style="font-size:14px;color:#C9D1D9;margin-top:10px;line-height:1.5;">'
            f'<span title="Kalshi YES implied probability">Kalshi <b>{cents_v*100:.0f}%</b></span>'
            f' &nbsp;·&nbsp; <span title="Our sim\'s probability">Sim <b>{sim_p*100:.0f}%</b></span>'
            f'</div>'
            f'<div style="font-size:15px;margin-top:6px;">{edge_pill}</div>'
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
        f'<div style="margin-top:10px;padding:16px 18px;background:#0E1117;'
        f'border:1px solid #2D333B;border-radius:10px;">'
        f'<div style="font-size:13px;color:#8B949E;text-transform:uppercase;'
        f'letter-spacing:0.08em;font-weight:600;margin-bottom:12px;">Kalshi markets</div>'
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;">{body}</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Render — yellow full-width divider between games
# ---------------------------------------------------------------------------
# Negative left/right margins extend the rule beyond the .block-container's
# horizontal padding so the line spans the full viewport width. The 100vw
# trick in calc() means the rule starts at the very left edge no matter how
# wide the page.
GAME_DIVIDER = (
    '<div style="height:5px;'
    'background:#F0B93C;'
    'margin:48px calc(50% - 50vw) 28px calc(50% - 50vw);'
    'width:100vw;'
    'box-shadow:0 0 12px rgba(240,185,60,0.45);"></div>'
)

for i, (_, row) in enumerate(sim.iterrows()):
    if i > 0:
        st.markdown(GAME_DIVIDER, unsafe_allow_html=True)
    st.markdown(game_header(row), unsafe_allow_html=True)
    st.markdown(winprob_bar(row),  unsafe_allow_html=True)
    lp = lineup_panel(row)
    if lp:
        st.markdown(lp, unsafe_allow_html=True)
    st.markdown(secondary_markets(row), unsafe_allow_html=True)
    st.markdown(kalshi_panel(row),   unsafe_allow_html=True)

st.divider()
st.caption(
    "Edges shown are simulator probability minus Kalshi implied probability. "
    "Positive = sim says more likely than market. "
    "Calibration blurbs draw on a 13,708-match historical backtest. "
    "PITCH is research; not betting advice."
)

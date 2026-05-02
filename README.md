# PITCH

**Calibrated soccer predictions across the top-5 European leagues, UCL, UEL, and MLS — with daily Kalshi market comparison.**

This repository powers the public [PITCH Streamlit app](https://share.streamlit.io). It contains **only** the display layer (Streamlit pages + cached parquets). The model code, scrapers, and pipelines live in a private repository.

## Pages

- **⚽ Today's Slate** — every game today with calibrated probabilities, expected scoreline, totals, BTTS, and Kalshi market edges.
- **📊 Calibration** — when the sim says X%, what actually happens? Per-market calibration tables from a 13.7K-match backtest.
- **🎯 Picks Tracker** — every pick we've ever made vs Kalshi, with lifetime ROI and per-market hit rate.
- **🔍 Match Explorer** — pick any team, opponent, and date — get the same prediction we'd have made that day.
- **📈 Backtest** — the headline numbers behind the model.
- **📖 How It Works** — methodology in plain English.
- **📚 Sources** — data source credits.

## Run locally

```bash
pip install -r requirements.txt
streamlit run pitch_explorer/app.py
```

## Auto-refresh

Parquets in `output/` are refreshed by the private model repo every morning around 3:30 AM CT and pushed here so Streamlit auto-redeploys.

## Disclaimer

PITCH is a research project. Not betting advice.

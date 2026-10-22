"""Print-size charts for the one-pager (PNG 300 dpi + SVG) into charts/."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA, CALC, OUT = ROOT / "data", ROOT / "calc", ROOT / "charts"
OUT.mkdir(exist_ok=True)

NAVY, GREEN, BRICK, GREY, INK, MUTED = "#13294B", "#1E6B47", "#A3361F", "#9AA0A6", "#222222", "#6B7075"

available = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((f for f in ["Inter", "Helvetica Neue", "Helvetica", "Arial"] if f in available), "DejaVu Sans")
plt.rcParams.update({
    "font.family": FONT, "font.size": 7.5, "axes.titlesize": 8.5, "axes.titleweight": "bold",
    "axes.edgecolor": GREY, "axes.linewidth": 0.6, "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white", "svg.fonttype": "none",
})


def finish(fig, ax, title, source, name):
    ax.set_title(title, loc="left", color=INK, pad=6)
    fig.text(0.01, 0.01, source, fontsize=7, color=MUTED, ha="left", va="bottom")
    for ext, kw in (("png", {"dpi": 300}), ("svg", {})):
        fig.savefig(OUT / f"{name}.{ext}", facecolor="white", **kw)
    plt.close(fig)


def series(df, metric):
    s = df[df.metric == metric].set_index("period").value
    return pd.to_numeric(s, errors="coerce")


# ------------------------------------------------------------- 1. hook: European ETF flows
theme = pd.read_csv(DATA / "theme.csv", dtype={"value": str})
flows = series(theme, "etf_eu_net_inflows")
labels = [p.replace("FY", "") for p in flows.index]
labels[-1] = "2026\nJan–Sep"
fig, ax = plt.subplots(figsize=(7.0, 1.8))
fig.subplots_adjust(left=0.01, right=0.74, top=0.80, bottom=0.25)
colors = [GREY] * (len(flows) - 1) + [NAVY]
bars = ax.bar(range(len(flows)), flows.values, color=colors, width=0.62)
for b, v, c in zip(bars, flows.values, colors):
    ax.text(b.get_x() + b.get_width() / 2, v + 8, f"${v:.0f}bn", ha="center", va="bottom",
            fontsize=7, color=NAVY if c == NAVY else MUTED, fontweight="bold" if c == NAVY else "normal")
ax.set_xticks(range(len(flows)), labels)
ax.tick_params(axis="x", length=0)
ax.set_yticks([])
ax.spines["left"].set_visible(False)
ax.set_ylim(0, flows.max() * 1.22)
note_x = 0.765
fig.text(note_x, 0.62, "Germany's pension depot\nstarts 1 Jan 2027", fontsize=7.5, color=NAVY, va="center")
fig.text(note_x, 0.36, "Austria's occupational\npension reform: 2028", fontsize=7.5, color=NAVY, va="center")
finish(fig, ax, "Nine months of 2026 already beat Europe's record ETF year",
       "Source: ETFGI year-end and Sep 2026 press releases (net inflows, US$)", "hook_etf_flows")

# ------------------------------------------------------------- 2. long: forward P/E vs peers
peers = pd.read_csv(DATA / "peers.csv").set_index("ticker")
sel = ["DWS.DE", "AMUN.PA", "N91.L", "JUP.L", "ABDN.L"]
pe = peers.loc[sel, ["name", "pe_forward"]].sort_values("pe_forward")
median = peers.loc[sel[1:], "pe_forward"].median()
fig, ax = plt.subplots(figsize=(3.3, 2.1))
fig.subplots_adjust(left=0.24, right=0.95, top=0.82, bottom=0.17)
y = np.arange(len(pe))
cols = [GREEN if t == "DWS.DE" else GREY for t in pe.index]
ax.barh(y, pe.pe_forward, color=cols, height=0.6)
for yi, (t, r) in zip(y, pe.iterrows()):
    ax.text(r.pe_forward + 0.2, yi, f"{r.pe_forward:.1f}x", va="center", fontsize=7,
            color=GREEN if t == "DWS.DE" else MUTED, fontweight="bold" if t == "DWS.DE" else "normal")
ax.set_yticks(y, [r["name"] for _, r in pe.iterrows()])
ax.tick_params(axis="y", length=0)
for lbl, t in zip(ax.get_yticklabels(), pe.index):
    if t == "DWS.DE":
        lbl.set_color(GREEN); lbl.set_fontweight("bold")
ax.axvline(median, color=INK, lw=0.7, ls=(0, (3, 2)))
ax.text(median + 0.15, -0.75, f"peer median {median:.1f}x", fontsize=7, color=INK, ha="left", va="center")
ax.set_xticks([]); ax.spines["bottom"].set_visible(False); ax.spines["left"].set_visible(False)
ax.set_xlim(0, pe.pe_forward.max() * 1.18)
ax.set_ylim(-1.1, len(pe) - 0.4)
for yi, (t, r) in zip(y, pe.iterrows()):  # keep value labels clear of the median line
    if abs(r.pe_forward - median) < 0.6 and r.pe_forward < median:
        ax.texts[list(pe.index).index(t)].set_x(median + 0.2)
finish(fig, ax, "DWS trades only slightly above peers",
       f"P/E on current-year consensus EPS. Source: Yahoo Finance, {peers.loc['DWS.DE', 'price_date']}",
       "dws_pe_vs_peers")

# ------------------------------------------------------------- 3. short: EPS vs dividend
hist = pd.read_csv(CALC / "ashm_history.csv").set_index("period").loc["FY2022":"FY2026"]
x = np.arange(len(hist)); w = 0.36
fig, ax = plt.subplots(figsize=(3.3, 2.1))
fig.subplots_adjust(left=0.04, right=0.98, top=0.80, bottom=0.17)
ax.bar(x - w / 2 - 0.01, hist.eps_diluted, w, color=GREY)
ax.bar(x + w / 2 + 0.01, hist.eps_adj_diluted, w, color=BRICK)
for xi, (h, c) in enumerate(zip(hist.eps_diluted, hist.eps_adj_diluted)):
    ax.text(xi - w / 2, h + 0.4, f"{h:.1f}", ha="center", fontsize=7, color=MUTED)
    ax.text(xi + w / 2, c + 0.4, f"{c:.1f}", ha="center", fontsize=7, color=BRICK,
            fontweight="bold" if xi == len(hist) - 1 else "normal")
ax.plot(x, hist.dps_total, color=INK, lw=1, marker="o", ms=3)
ax.text(x[2], hist.dps_total.iloc[2] + 0.8, "Dividend 16.9p", fontsize=7, color=INK, ha="center")
ax.annotate("statutory", (x[0] - w / 2, hist.eps_diluted.iloc[0] / 2), fontsize=7, color="white",
            ha="center", va="center", rotation=90)
ax.annotate("core", (x[0] + w / 2, hist.eps_adj_diluted.iloc[0] / 2), fontsize=7, color="white",
            ha="center", va="center", rotation=90)
ax.set_xticks(x, [p.replace("FY20", "FY") for p in hist.index])
ax.tick_params(axis="x", length=0)
ax.set_yticks([]); ax.spines["left"].set_visible(False)
ax.set_ylim(0, 21)
finish(fig, ax, "Ashmore pays out more than its core business earns",
       "Diluted EPS vs adjusted EPS, pence. Source: Ashmore results FY2022–26", "ashm_eps_vs_dividend")

# ------------------------------------------------------------- 3b. long: passive/Xtrackers AuM
dws = pd.read_csv(DATA / "dws.csv", dtype={"value": str})
passive = series(dws, "aum_passive").loc[["FY2023", "FY2024", "FY2025", "H1 2026"]]
growth = passive.iloc[-1] / passive.iloc[0] - 1
fig, ax = plt.subplots(figsize=(3.3, 2.1))
fig.subplots_adjust(left=0.04, right=0.98, top=0.80, bottom=0.17)
cols = [GREY] * (len(passive) - 1) + [GREEN]
bars = ax.bar(range(len(passive)), passive.values, color=cols, width=0.6)
for b, v, c in zip(bars, passive.values, cols):
    ax.text(b.get_x() + b.get_width() / 2, v + 8, f"€{v:.0f}bn", ha="center", va="bottom", fontsize=7,
            color=GREEN if c == GREEN else MUTED, fontweight="bold" if c == GREEN else "normal")
ax.set_xticks(range(len(passive)), [p.replace("FY", "") for p in passive.index])
ax.tick_params(axis="x", length=0)
ax.set_yticks([]); ax.spines["left"].set_visible(False)
ax.set_ylim(0, passive.max() * 1.18)
finish(fig, ax, f"DWS’s ETF business grew {100 * growth:.0f}% in 2½ years",
       "Source: DWS annual reports and H1 2026 report", "dws_passive_aum")

# ------------------------------------------------------------- 4. optional price charts
def price_chart(csv, colour, title, unit, events, source, name):
    px = pd.read_csv(DATA / csv, parse_dates=["date"]).set_index("date").Close
    fig, ax = plt.subplots(figsize=(3.3, 1.6))
    fig.subplots_adjust(left=0.10, right=0.86, top=0.80, bottom=0.24)
    ax.plot(px.index, px.values, color=colour, lw=1)
    for d, txt, (tx, ty) in events:  # (tx, ty): label position in data coordinates
        d = pd.Timestamp(d)
        v = px.asof(d)
        ax.plot([d], [v], "o", color=colour, ms=3)
        ax.annotate(txt, (d, v), xytext=(pd.Timestamp(tx), ty), fontsize=7, color=INK, ha="right",
                    va="center", arrowprops=dict(arrowstyle="-", color=GREY, lw=0.5, shrinkB=3))
    ax.text(px.index[-1], px.iloc[-1], f" {px.iloc[-1]:.{1 if unit == 'p' else 2}f}{unit}",
            fontsize=7, color=colour, va="center", ha="left", fontweight="bold")
    ax.set_xlim(px.index[0], px.index[-1] + pd.Timedelta(days=20))
    ax.set_ylim(px.min() * 0.9, px.max() * 1.15)
    ax.tick_params(length=2)
    finish(fig, ax, title, source, name)


price_chart("prices_dws.csv", GREEN, "DWS: five years, close in EUR", "€",
            [("2026-01-29", "FY25 results, special\ndividend plan", ("2025-09-01", 82))],
            "Source: Yahoo Finance (DWS.DE), daily close", "dws_price_5y")
price_chart("prices_ashm.csv", BRICK, "Ashmore: five years, close in pence", "p",
            [("2026-09-07", "FY26 results", ("2026-03-15", 345))],
            "Source: Yahoo Finance (ASHM.L), daily close", "ashm_price_5y")
print("font:", FONT, "| charts written to", OUT)

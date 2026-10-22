"""Valuation maths for the pitch. All inputs come from data/*.csv; scenario knobs are below.

Writes calc/dws_scenarios.csv, calc/dws_sensitivity.csv, calc/ashm_scenarios.csv,
calc/ashm_sensitivity.csv, calc/ashm_history.csv and calc/summary.csv, and prints the summary.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA, CALC = ROOT / "data", ROOT / "calc"
CALC.mkdir(exist_ok=True)

# ---------------------------------------------------------------- scenario inputs (edit freely)
DWS_SCENARIOS = {            # name: (EPS 2027E growth vs 2026E consensus, exit P/E)
    "Bear": (0.00, 11.0),
    "Base": (0.125, 13.0),
    "Bull": (0.15, 14.0),
}
DWS_GRID_GROWTH = [0.00, 0.05, 0.10, 0.125, 0.15]
DWS_GRID_PE = [10, 11, 12, 13, 14, 15]
DWS_PAYOUT = 0.65            # management's ordinary payout target, used if no DPS consensus

ASHM_SCENARIOS = {           # name: (core EPS in pence, P/E)
    "Bear for us (good for the short)": (5.0, 15.0),
    "Base": (7.1, 15.0),
    "Against us": (10.0, 20.0),
}
ASHM_GRID_EPS = [4, 5, 6, 7, 8, 9, 10]
ASHM_GRID_PE = [10, 12, 14, 15, 16, 18, 20]

DWS_PEERS = ["AMUN.PA", "N91.L", "JUP.L", "ABDN.L"]
ASHM_PEERS = ["N91.L", "JUP.L", "ABDN.L", "LIO.L", "POLR.L"]
GLOBAL_REF = ["TROW", "BEN", "BLK"]


def load(name):
    return pd.read_csv(DATA / f"{name}.csv", dtype={"value": str})


def get(df, metric, period=None):
    """Return the numeric value of a metric (optionally for one period) plus its source URL."""
    sel = df[df.metric == metric]
    if period is not None:
        sel = sel[sel.period == period]
    if len(sel) != 1:
        raise KeyError(f"{metric} / {period}: {len(sel)} rows")
    r = sel.iloc[0]
    return float(r.value), r.source_url


summary = []


def note(section, item, value, unit, source, formula=""):
    summary.append({"section": section, "item": item, "value": value, "unit": unit,
                    "formula": formula, "source": source})


# ---------------------------------------------------------------- inputs
dws, ashm, peers = load("dws"), load("ashmore"), pd.read_csv(DATA / "peers.csv")
peers = peers[peers.group != "excluded"].set_index("ticker")

dws_px, src_px = get(dws, "price_close")
dws_eps26, src_cons = get(dws, "cons_eps", "FY2026E")
dws_eps27_cons, _ = get(dws, "cons_eps", "FY2027E")
dws_eps25, src_fy25 = get(dws, "eps", "FY2025")
dws_dps26 = round(DWS_PAYOUT * dws_eps26, 2)       # brief's consensus EUR 3.40 not verifiable for free
dws_shares = 200.0

ash_px, src_apx = get(ashm, "price_close")
ash_eps, src_fy26 = get(ashm, "eps_diluted", "FY2026")
ash_core, _ = get(ashm, "eps_adj_diluted", "FY2026")
ash_core25, _ = get(ashm, "eps_adj_diluted", "FY2025")
ash_dps, _ = get(ashm, "dps_total", "FY2026")
ash_pbt, _ = get(ashm, "pbt", "FY2026")
ash_seed, _ = get(ashm, "seed_capital_gains", "FY2026")
ash_xs_ps, _ = get(ashm, "excess_capital_ps")
ash_xs, _ = get(ashm, "excess_capital")
ash_issued, _ = get(ashm, "shares_in_issue")
ash_ex_ebt, src_shares = get(ashm, "shares_ex_ebt")
ash_diluted, _ = get(ashm, "shares_diluted_wavg")
ash_cons_fy27, src_acons = get(ashm, "cons_eps_adj", "FY2027E (Jun-27)")

# ---------------------------------------------------------------- DWS
pe26 = dws_px / dws_eps26
yld26 = dws_dps26 / dws_px
note("DWS", "Share price", dws_px, "EUR (22 Oct 2026 close)", src_px)
note("DWS", "Market cap", dws_px * dws_shares / 1000, "EUR bn", src_px, "price x 200.0m shares")
note("DWS", "P/E 2026E", round(pe26, 1), "x", src_cons, "price / consensus EPS 2026E (5.22)")
note("DWS", "P/E 2027E", round(dws_px / dws_eps27_cons, 1), "x", src_cons, "price / consensus EPS 2027E")
note("DWS", "P/E trailing FY2025", round(dws_px / dws_eps25, 1), "x", src_fy25, "price / FY2025 EPS 4.64")
note("DWS", "DPS 2026E (65% payout)", dws_dps26, "EUR", src_cons, "0.65 x EPS 2026E")
note("DWS", "Dividend yield 2026E", round(100 * yld26, 1), "%", src_cons, "DPS 2026E / price")
note("DWS", "Dividend yield trailing (FY2025 DPS 3.00)", round(100 * 3.00 / dws_px, 1), "%", src_fy25)

dws_peer_pe = peers.loc[DWS_PEERS, "pe_forward"]
dws_peer_med = dws_peer_pe.median()
note("DWS", "Peer median forward P/E (Amundi, Ninety One, Jupiter, Aberdeen)", round(dws_peer_med, 1), "x",
     "data/peers.csv (Yahoo consensus)", "median of price / current-FY consensus EPS")
note("DWS", "Implied price at peer median P/E", round(dws_peer_med * dws_eps26, 2), "EUR",
     "data/peers.csv", "peer median x EPS 2026E")
note("DWS", "Global reference median forward P/E (TROW, BEN, BLK)",
     round(peers.loc[GLOBAL_REF, "pe_forward"].median(), 1), "x", "data/peers.csv")

rows = []
for name, (g, pe) in DWS_SCENARIOS.items():
    eps27 = dws_eps26 * (1 + g)
    target = eps27 * pe
    upside = target / dws_px - 1
    total = (target + dws_dps26) / dws_px - 1
    rows.append({"scenario": name, "eps_growth_vs_2026E": g, "eps_2027E": round(eps27, 2), "exit_pe": pe,
                 "target_price": round(target, 2), "upside_pct": round(100 * upside, 1),
                 "dividend_12m": dws_dps26, "total_return_pct": round(100 * total, 1)})
    note("DWS", f"{name} target (EPS x{1 + g:.3f}, {pe:.0f}x)", round(target, 2), "EUR", src_cons,
         "EPS 2026E x (1+g) x P/E")
    note("DWS", f"{name} total return incl. 1y dividend", round(100 * total, 1), "%", src_cons,
         "(target + DPS 2026E) / price - 1")
pd.DataFrame(rows).to_csv(CALC / "dws_scenarios.csv", index=False)

grid = []
for g in DWS_GRID_GROWTH:
    for pe in DWS_GRID_PE:
        p = dws_eps26 * (1 + g) * pe
        grid.append({"eps_growth": g, "pe": pe, "implied_price": round(p, 2),
                     "upside_pct": round(100 * (p / dws_px - 1), 1)})
pd.DataFrame(grid).to_csv(CALC / "dws_sensitivity.csv", index=False)

# ---------------------------------------------------------------- Ashmore
hist = (ashm[ashm.period.str.fullmatch(r"FY20\d\d")]
        .pivot_table(index="period", columns="metric", values="value", aggfunc="first"))
num = hist[["eps_diluted", "eps_adj_diluted", "dps_total", "pbt", "seed_capital_gains"]].astype(float)
num["cover_statutory"] = (num.eps_diluted / num.dps_total).round(2)
num["cover_core"] = (num.eps_adj_diluted / num.dps_total).round(2)
num["dps_over_core_eps"] = (num.dps_total / num.eps_adj_diluted).round(2)
num["seed_pct_pbt"] = (100 * num.seed_capital_gains / num.pbt).round(1)
num["headline_minus_core_p"] = (num.eps_diluted - num.eps_adj_diluted).round(1)
num.to_csv(CALC / "ashm_history.csv")

pe_head = ash_px / ash_eps
pe_core = ash_px / ash_core
mcap_ex_ebt = ash_px * ash_ex_ebt / 100 / 1000      # GBp x m shares -> GBP bn
mcap_issued = ash_px * ash_issued / 100 / 1000
note("Ashmore", "Share price", ash_px, "GBp (22 Oct 2026 close)", src_apx)
note("Ashmore", "Market cap (ex-EBT shares, 650.8m)", round(mcap_ex_ebt, 3), "GBP bn", src_shares,
     "price x shares in issue less EBT holding")
note("Ashmore", "Market cap (all issued shares, 712.7m)", round(mcap_issued, 3), "GBP bn", src_fy26)
note("Ashmore", "Headline P/E (FY2026 diluted EPS 15.0p)", round(pe_head, 1), "x", src_fy26, "price / diluted EPS")
note("Ashmore", "Core P/E (FY2026 adjusted diluted EPS 5.0p)", round(pe_core, 1), "x", src_fy26,
     "price / adjusted diluted EPS")
note("Ashmore", "Core P/E ex excess capital", round((ash_px - ash_xs_ps) / ash_core, 1), "x", src_fy26,
     "(price - 73p) / 5.0p")
note("Ashmore", "Forward P/E (FY2027E consensus 7.04p)", round(ash_px / ash_cons_fy27, 1), "x", src_acons)
note("Ashmore", "Dividend yield (16.9p)", round(100 * ash_dps / ash_px, 1), "%", src_fy26)
note("Ashmore", "DPS / core EPS", round(ash_dps / ash_core, 2), "x", src_fy26, "16.9 / 5.0")
note("Ashmore", "Dividend cover on core EPS", round(ash_core / ash_dps, 2), "x", src_fy26, "5.0 / 16.9")
note("Ashmore", "Dividend cover on statutory EPS", round(ash_eps / ash_dps, 2), "x", src_fy26, "15.0 / 16.9 (company: 0.9)")
note("Ashmore", "Seed gains as % of PBT", round(100 * ash_seed / ash_pbt, 1), "%", src_fy26, "82.5 / 126.9")
note("Ashmore", "Excess capital per share on ex-EBT shares", round(100 * ash_xs / ash_ex_ebt, 1), "p", src_fy26,
     "GBP 521.5m / 650.8m (company's 73p uses 712.7m issued)")
note("Ashmore", "Excess capital per share on diluted shares", round(100 * ash_xs / ash_diluted, 1), "p", src_fy26,
     "GBP 521.5m / 686.8m")

rows = []
for name, (eps, pe) in ASHM_SCENARIOS.items():
    value = eps * pe + ash_xs_ps
    rows.append({"scenario": name, "core_eps_p": eps, "pe": pe, "excess_capital_p": ash_xs_ps,
                 "implied_value_p": round(value, 1), "move_pct": round(100 * (value / ash_px - 1), 1)})
    note("Ashmore", f"{name}: {eps}p x {pe:.0f} + {ash_xs_ps:.0f}p", round(value, 1), "GBp", src_fy26,
         "core EPS x P/E + excess capital per share")
    note("Ashmore", f"{name}: move vs price", round(100 * (value / ash_px - 1), 1), "%", src_fy26)
pd.DataFrame(rows).to_csv(CALC / "ashm_scenarios.csv", index=False)

grid = []
for eps in ASHM_GRID_EPS:
    for pe in ASHM_GRID_PE:
        v = eps * pe + ash_xs_ps
        grid.append({"core_eps_p": eps, "pe": pe, "implied_value_p": round(v, 1),
                     "move_pct": round(100 * (v / ash_px - 1), 1)})
pd.DataFrame(grid).to_csv(CALC / "ashm_sensitivity.csv", index=False)

# break-even multiple: what P/E on core EPS justifies today's price after excess capital
note("Ashmore", "P/E on 5.0p needed to justify price (after 73p)", round((ash_px - ash_xs_ps) / ash_core, 1), "x",
     src_fy26, "(price - 73) / 5.0")
note("Ashmore", "Core EPS needed at 15x to justify price", round((ash_px - ash_xs_ps) / 15, 1), "p", src_fy26,
     "(price - 73) / 15")

ap = peers.loc[ASHM_PEERS]
note("Peers", "Ashmore peer median trailing P/E", round(ap.pe_trailing.median(), 1), "x", "data/peers.csv")
note("Peers", "Ashmore peer median forward P/E", round(ap.pe_forward.median(), 1), "x", "data/peers.csv")
note("Peers", "Ashmore peer median dividend yield", round(ap.div_yield_pct.median(), 1), "%", "data/peers.csv")
note("Peers", "DWS peer median dividend yield", round(peers.loc[DWS_PEERS, "div_yield_pct"].median(), 1), "%",
     "data/peers.csv")
for t, r in peers.iterrows():
    note("Peers", f"{r['name']} ({t}) fwd P/E [{r.fy_basis}]", round(r.pe_forward, 1), "x", r.source_url,
         f"trailing {r.pe_trailing:.1f}x, yield {r.div_yield_pct:.2f}%")

out = pd.DataFrame(summary)
out.to_csv(CALC / "summary.csv", index=False)
with pd.option_context("display.width", 200, "display.max_colwidth", 60, "display.max_rows", 200):
    print(out[["section", "item", "value", "unit", "formula"]].to_string(index=False))
    print("\nAshmore history\n", num.to_string())

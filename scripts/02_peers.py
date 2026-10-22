"""Build data/peers.csv from yfinance quote + consensus EPS estimates.

Forward P/E is defined consistently for every company as
    price / consensus EPS for the current (next-to-report) fiscal year  ("0y" on Yahoo).
Fiscal year ends differ (Dec, Mar, Jun, Sep), so the `fy_basis` column records which year that is.
LSE quotes are in pence while Yahoo EPS for LSE names is in GBP, so EPS is converted to pence.
"""
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today().isoformat()

# ticker, name, group, fiscal year end, note
PEERS = [
    ("DWS.DE", "DWS Group", "subject", "Dec", ""),
    ("ASHM.L", "Ashmore Group", "subject", "Jun", ""),
    ("AMUN.PA", "Amundi", "DWS peer", "Dec", ""),
    ("N91.L", "Ninety One", "both", "Mar", ""),
    ("JUP.L", "Jupiter", "both", "Dec", ""),
    ("ABDN.L", "Aberdeen", "both", "Dec", ""),
    ("LIO.L", "Liontrust", "Ashmore peer", "Mar", ""),
    ("POLR.L", "Polar Capital", "Ashmore peer", "Mar", ""),
    ("TROW", "T. Rowe Price", "global reference", "Dec", ""),
    ("BEN", "Franklin Resources", "global reference", "Sep", ""),
    ("BLK", "BlackRock", "global reference", "Dec", ""),
]
EXCLUDED = {"SDR.L": "Schroders excluded: acquired by Nuveen (590p cash offer, announced 12 Feb 2026), "
                     "price pinned to the deal"}


def fy_label(fye, today=date.today()):
    """Label of the current (next-to-report) fiscal year, e.g. 'FY Dec-2026'."""
    month = {"Dec": 12, "Mar": 3, "Jun": 6, "Sep": 9}[fye]
    year = today.year if today.month <= month else today.year + 1
    return f"FY {fye}-{year}"


def row(ticker, name, group, fye, note):
    t = yf.Ticker(ticker)
    info = t.info
    est = t.earnings_estimate
    pence = info.get("currency") == "GBp"
    scale = 100 if pence else 1  # Yahoo EPS/DPS for LSE names are in GBP
    price = info.get("regularMarketPrice")
    eps_fy0 = est.loc["0y", "avg"] * scale if est is not None and "0y" in est.index else None
    eps_fy1 = est.loc["+1y", "avg"] * scale if est is not None and "+1y" in est.index else None
    n_fy0 = est.loc["0y", "numberOfAnalysts"] if est is not None and "0y" in est.index else None
    eps_ttm = info.get("trailingEps") * scale if info.get("trailingEps") is not None else None
    dps = info.get("dividendRate") * scale if info.get("dividendRate") is not None else None
    return {
        "ticker": ticker, "name": name, "group": group, "currency": info.get("currency"),
        "price": price, "price_date": TODAY,
        "eps_ttm": eps_ttm, "pe_trailing": price / eps_ttm if eps_ttm else None,
        "pe_trailing_yahoo": info.get("trailingPE"),
        "fy_basis": fy_label(fye), "eps_fy0_cons": eps_fy0, "n_analysts_fy0": n_fy0,
        "pe_forward": price / eps_fy0 if eps_fy0 else None,
        "eps_fy1_cons": eps_fy1, "pe_fy1": price / eps_fy1 if eps_fy1 else None,
        "dps_indicated": dps, "div_yield_pct": info.get("dividendYield"),
        "market_cap": info.get("marketCap"), "market_cap_ccy": "GBP" if pence else info.get("currency"),
        "source_url": f"https://finance.yahoo.com/quote/{ticker}/", "accessed": TODAY,
        "notes": note,
    }


if __name__ == "__main__":
    rows = []
    for p in PEERS:
        try:
            rows.append(row(*p))
        except Exception as e:
            print(f"!! {p[0]} failed: {e}")
            rows.append({"ticker": p[0], "name": p[1], "group": p[2], "notes": f"NOT FOUND: {e}"})
    for tk, why in EXCLUDED.items():
        rows.append({"ticker": tk, "name": "Schroders", "group": "excluded", "notes": why,
                     "source_url": "https://www.investegate.co.uk/announcement/rns/schroders--sdr/offer-for-schroders-plc/9426823",
                     "accessed": TODAY})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "data" / "peers.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(df[["ticker", "currency", "price", "pe_trailing", "pe_trailing_yahoo", "fy_basis",
                  "eps_fy0_cons", "n_analysts_fy0", "pe_forward", "pe_fy1", "div_yield_pct", "market_cap"]].round(2))

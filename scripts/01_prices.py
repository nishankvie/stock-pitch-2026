"""Download 5y daily prices and snapshot quote data for DWS, Ashmore and peers via yfinance.

Writes data/prices_dws.csv, data/prices_ashm.csv and data/peers_yahoo_raw.csv.
LSE tickers are quoted by Yahoo in pence (GBp); values are kept in pence.
"""
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TODAY = date.today().isoformat()

PEERS = ["DWS.DE", "ASHM.L", "AMUN.PA", "N91.L", "JUP.L", "ABDN.L", "LIO.L",
         "POLR.L", "TROW", "BEN", "BLK"]
FIELDS = ["currency", "regularMarketPrice", "previousClose", "trailingPE", "forwardPE",
          "trailingEps", "forwardEps", "dividendYield", "trailingAnnualDividendYield",
          "dividendRate", "marketCap", "sharesOutstanding", "fiftyTwoWeekHigh",
          "fiftyTwoWeekLow", "targetMeanPrice", "targetLowPrice", "targetHighPrice",
          "numberOfAnalystOpinions", "recommendationKey"]


def history(ticker, out):
    df = yf.Ticker(ticker).history(period="5y", auto_adjust=False)
    if df.empty:
        print(f"!! yfinance returned no history for {ticker}")
        return None
    df.index = df.index.tz_localize(None).date
    df.index.name = "date"
    df[["Open", "High", "Low", "Close", "Adj Close", "Volume"]].to_csv(DATA / out)
    last = df.iloc[-1]
    last_year = df.loc[df.index >= (df.index[-1] - pd.Timedelta(days=365))]
    print(f"{ticker}: last close {last['Close']:.2f} on {df.index[-1]}; "
          f"52w high {last_year['High'].max():.2f} ({last_year['High'].idxmax()}), "
          f"52w low {last_year['Low'].min():.2f} ({last_year['Low'].idxmin()}); "
          f"52w close high {last_year['Close'].max():.2f} ({last_year['Close'].idxmax()}), "
          f"close low {last_year['Close'].min():.2f} ({last_year['Close'].idxmin()})")
    return df


def snapshot():
    rows = []
    for t in PEERS:
        try:
            info = yf.Ticker(t).info
        except Exception as e:  # yfinance occasionally fails on .info
            print(f"!! info failed for {t}: {e}")
            info = {}
        rows.append({"ticker": t, "accessed": TODAY, **{f: info.get(f) for f in FIELDS}})
    pd.DataFrame(rows).to_csv(DATA / "peers_yahoo_raw.csv", index=False)
    print(pd.DataFrame(rows).to_string())


if __name__ == "__main__":
    history("DWS.DE", "prices_dws.csv")
    history("ASHM.L", "prices_ashm.csv")
    snapshot()

import json
from datetime import datetime
import pandas as pd
import pytz
import yfinance as yf

# Combined Watchlist
WATCHLIST = [
    # Large-Cap Core
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "BHARTIARTL.NS",
    "LT.NS",
    "SBIN.NS",
    "AXISBANK.NS",
    "TITAN.NS",
    "ITC.NS",
    "SUNPHARMA.NS",
    "MARUTI.NS",
    "BAJFINANCE.NS",
    # Fundamental Small-Caps
    "CAMS.NS",
    "NESCO.NS",
    "CLEAN.NS",
    "IONEXCHANG.NS",
    "CASTROLIND.NS",
]

# Sectors where Debt-to-Equity is structurally high and should not be penalized
FINANCIAL_STOCKS = ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "BAJFINANCE"]


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
  delta = series.diff()
  gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
  loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
  rs = gain / loss
  return 100.0 - (100.0 / (1.0 + rs))


def evaluate_fundamentals(ticker_obj, symbol: str) -> dict:
  """Evaluates core fundamental health metrics.

  Returns fundamental score, metrics dict, and pass/fail boolean.
  """
  try:
    info = ticker_obj.info or {}

    roe = info.get("returnOnEquity")
    debt_to_eq = info.get("debtToEquity")  # Yahoo often reports 0.5 as 50
    profit_margin = info.get("profitMargins")
    earnings_growth = info.get("earningsGrowth")

    # Format values safely
    roe_val = round(roe * 100, 1) if roe is not None else None
    pm_val = round(profit_margin * 100, 1) if profit_margin is not None else None
    eg_val = (
        round(earnings_growth * 100, 1) if earnings_growth is not None else None
    )

    # In yfinance, debtToEquity is often represented as percentage (e.g. 50 = 0.5x)
    de_val = None
    if debt_to_eq is not None:
      de_val = (
          round(debt_to_eq / 100, 2) if debt_to_eq > 10 else round(debt_to_eq, 2)
      )

    # Check conditions
    roe_pass = roe_val is not None and roe_val >= 15.0
    pm_pass = pm_val is not None and pm_val >= 10.0
    eg_pass = eg_val is not None and eg_val > 0.0

    # Debt check (skipped for Banks & NBFCs as debt is their raw operating inventory)
    if symbol in FINANCIAL_STOCKS:
      de_pass = True
      de_str = "N/A (Bank)"
    else:
      de_pass = de_val is not None and de_val <= 1.0
      de_str = f"{de_val}x" if de_val is not None else "N/A"

    # Strict Fundamental Quality: ROE >= 15%, Reasonable Debt, Solid Margins
    is_fund_strong = bool(roe_pass and de_pass and pm_pass)

    return {
        "roe": f"{roe_val}%" if roe_val is not None else "N/A",
        "de": de_str,
        "net_margin": f"{pm_val}%" if pm_val is not None else "N/A",
        "earnings_growth": f"{eg_val}%" if eg_val is not None else "N/A",
        "fund_strong": is_fund_strong,
    }
  except Exception:
    return {
        "roe": "N/A",
        "de": "N/A",
        "net_margin": "N/A",
        "earnings_growth": "N/A",
        "fund_strong": False,
    }


def run_scan():
  ist = pytz.timezone("Asia/Kolkata")
  timestamp_ist = datetime.now(ist).strftime("%Y-%m-%d %I:%M %p IST")

  matches = []
  all_data = []

  print(f"Starting combined scan for {len(WATCHLIST)} symbols...")

  for ticker in WATCHLIST:
    symbol = ticker.replace(".NS", "")
    try:
      t = yf.Ticker(ticker)

      # 1. Price Action & Momentum Fetch (1 year daily)
      df = t.history(period="1y", interval="1d", auto_adjust=True)
      if df.empty or len(df) < 50:
        continue

      if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

      close = df["Close"]
      high = df["High"]
      volume = df["Volume"]

      ema_20 = close.ewm(span=20, adjust=False).mean()
      ema_50 = close.ewm(span=50, adjust=False).mean()
      rsi_series = calculate_rsi(close)

      curr_price = float(close.iloc[-1])
      curr_vol = float(volume.iloc[-1])
      avg_vol_20 = float(volume.iloc[-21:-1].mean())
      curr_rsi = float(rsi_series.iloc[-1])
      vol_multiplier = curr_vol / avg_vol_20 if avg_vol_20 > 0 else 0.0

      high_52w = float(high.max())
      pct_off_52w = ((high_52w - curr_price) / high_52w) * 100.0

      # Technical rules
      above_mas = (curr_price > ema_20.iloc[-1]) and (
          curr_price > ema_50.iloc[-1]
      )
      volume_surge = vol_multiplier >= 1.2
      rsi_valid = 50.0 <= curr_rsi <= 70.0
      near_52w_high = pct_off_52w <= 15.0
      tech_match = bool(
          above_mas and volume_surge and rsi_valid and near_52w_high
      )

      # 2. Fundamental Quality Check
      fund_metrics = evaluate_fundamentals(t, symbol)

      # Combined Conviction Flag: Both Technical Breakout + Strong Fundamentals
      high_conviction = bool(tech_match and fund_metrics["fund_strong"])

      item = {
          "symbol": symbol,
          "price": round(curr_price, 2),
          "high_52w": round(high_52w, 2),
          "pct_off_52w": round(pct_off_52w, 1),
          "vol_surge": round(vol_multiplier, 2),
          "rsi": round(curr_rsi, 1),
          "roe": fund_metrics["roe"],
          "de": fund_metrics["de"],
          "net_margin": fund_metrics["net_margin"],
          "fund_strong": fund_metrics["fund_strong"],
          "tech_match": tech_match,
          "matched": high_conviction,
      }
      all_data.append(item)

      if high_conviction:
        matches.append(item)
        print(f"[🔥 HIGH CONVICTION] {symbol:12} : Tech + Fundamentals ALIGNED")
      elif tech_match:
        print(
            f"[⚠️ TECH ONLY]       {symbol:12} : Technical setup valid,"
            " fundamentals weak/missing"
        )
      else:
        print(
            f"[-]                 {symbol:12} : Neutral (Vol"
            f" {vol_multiplier:.2f}x | RSI {curr_rsi:.1f})"
        )

    except Exception as e:
      print(f"[!] Error on {symbol}: {e}")
      continue

  payload = {
      "last_updated": timestamp_ist,
      "total_scanned": len(WATCHLIST),
      "match_count": len(matches),
      "matches": matches,
      "all_scanned": all_data,
  }

  with open("results.json", "w") as f:
    json.dump(payload, f, indent=2)

  print(
      f"\nScan completed at {timestamp_ist}. Found {len(matches)} high"
      " conviction setups."
  )


if __name__ == "__main__":
  run_scan()
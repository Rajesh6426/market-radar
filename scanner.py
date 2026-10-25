import json
from datetime import datetime
import pandas as pd
import pytz
import yfinance as yf

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


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
  delta = series.diff()
  gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
  loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
  rs = gain / loss
  return 100.0 - (100.0 / (1.0 + rs))


def run_scan():
  ist = pytz.timezone("Asia/Kolkata")
  timestamp_ist = datetime.now(ist).strftime("%Y-%m-%d %I:%M %p IST")

  matches = []
  all_data = []

  print(f"Starting scan for {len(WATCHLIST)} symbols...")

  for ticker in WATCHLIST:
    symbol = ticker.replace(".NS", "")
    try:
      # Download 1 year of daily history to accurately capture 52-week high
      df = yf.download(
          ticker, period="1y", interval="1d", progress=False, auto_adjust=True
      )

      if df.empty or len(df) < 50:
        continue

      if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

      close = df["Close"]
      high = df["High"]
      volume = df["Volume"]

      # Technical Indicators
      ema_20 = close.ewm(span=20, adjust=False).mean()
      ema_50 = close.ewm(span=50, adjust=False).mean()
      rsi_series = calculate_rsi(close)

      curr_price = float(close.iloc[-1])
      curr_vol = float(volume.iloc[-1])
      avg_vol_20 = float(volume.iloc[-21:-1].mean())
      curr_rsi = float(rsi_series.iloc[-1])
      vol_multiplier = curr_vol / avg_vol_20 if avg_vol_20 > 0 else 0.0

      # 52-Week High Calculation
      high_52w = float(high.max())
      pct_off_52w = ((high_52w - curr_price) / high_52w) * 100.0

      # Setup Criteria:
      # 1. Price above 20 & 50 EMA
      # 2. Volume expansion >= 1.2x
      # 3. Healthy momentum RSI (50 - 70)
      # 4. Proximity within 15% of 52-week high
      above_mas = (curr_price > ema_20.iloc[-1]) and (
          curr_price > ema_50.iloc[-1]
      )
      volume_surge = vol_multiplier >= 1.2
      rsi_valid = 50.0 <= curr_rsi <= 70.0
      near_52w_high = pct_off_52w <= 15.0

      is_match = bool(
          above_mas and volume_surge and rsi_valid and near_52w_high
      )

      item = {
          "symbol": symbol,
          "tv_symbol": f"NSE:{symbol}",
          "price": round(curr_price, 2),
          "high_52w": round(high_52w, 2),
          "pct_off_52w": round(pct_off_52w, 1),
          "vol_surge": round(vol_multiplier, 2),
          "rsi": round(curr_rsi, 1),
          "matched": is_match,
      }
      all_data.append(item)

      if is_match:
        matches.append(item)
        print(
            f"[✓ MATCH] {symbol:12} : Vol {vol_multiplier:.2f}x | RSI"
            f" {curr_rsi:.1f} | {pct_off_52w:.1f}% off 52W High"
        )
      else:
        print(
            f"[-] {symbol:12} : Vol {vol_multiplier:.2f}x | RSI {curr_rsi:.1f}"
            f" | {pct_off_52w:.1f}% off 52W High"
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
      f"\nScan completed at {timestamp_ist}. Found {len(matches)} qualified"
      " leaders."
  )


if __name__ == "__main__":
  run_scan()
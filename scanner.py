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

FINANCIAL_STOCKS = ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "BAJFINANCE"]


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
  delta = series.diff()
  gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
  loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
  rs = gain / loss
  return 100.0 - (100.0 / (1.0 + rs))


def classify_market_cap(mcap_raw):
  """Converts raw market cap to INR Crores and categorizes into Large, Mid, or Small Cap."""
  if not mcap_raw or mcap_raw <= 0:
    return "N/A", "Cap N/A"

  mcap_cr = round(mcap_raw / 10000000, 1)
  if mcap_cr >= 20000:
    cap_type = "Large-Cap"
  elif mcap_cr >= 5000:
    cap_type = "Mid-Cap"
  else:
    cap_type = "Small-Cap"

  return f"₹{mcap_cr:,.0f} Cr", cap_type


def evaluate_company_fundamentals(ticker_obj, symbol: str) -> dict:
  try:
    info = ticker_obj.info or {}

    # Market Cap (try fast_info fallback)
    raw_mcap = info.get("marketCap")
    if not raw_mcap:
      try:
        raw_mcap = getattr(ticker_obj.fast_info, "market_cap", None)
      except Exception:
        raw_mcap = None

    mcap_str, cap_category = classify_market_cap(raw_mcap)

    # P/E Ratio (fallback to forwardPE if trailing is missing)
    pe = info.get("trailingPE") or info.get("forwardPE")
    pe_val = round(pe, 1) if (pe and pe > 0) else None

    # PEG Ratio
    peg = info.get("pegRatio")
    peg_val = round(peg, 2) if (peg and peg > 0) else None

    # ROE
    roe = info.get("returnOnEquity")
    roe_val = round(roe * 100, 1) if roe is not None else None

    val_pass = (peg_val is not None and peg_val <= 2.5) or (
        pe_val is not None and pe_val <= 50
    )

    if symbol in FINANCIAL_STOCKS:
      # Banks / NBFCs
      roa = info.get("returnOnAssets")
      pb = info.get("priceToBook")

      roa_val = round(roa * 100, 2) if roa is not None else None
      pb_val = round(pb, 2) if pb is not None else None

      bank_sound = (
          (roa_val is not None and roa_val >= 1.0)
          and (roe_val is not None and roe_val >= 12.0)
          and val_pass
      )

      return {
          "sector_type": "BANK",
          "mcap_str": mcap_str,
          "cap_category": cap_category,
          "pe": f"{pe_val}x" if pe_val else "N/A",
          "peg": f"{peg_val}" if peg_val else "N/A",
          "roe": f"{roe_val}%" if roe_val else "N/A",
          "primary_label": "ROA",
          "primary_val": f"{roa_val}%" if roa_val else "N/A",
          "secondary_label": "P/B",
          "secondary_val": f"{pb_val}x" if pb_val else "N/A",
          "fund_strong": bool(bank_sound),
      }

    else:
      # Corporate / Non-Financials
      debt_to_eq = info.get("debtToEquity")
      margin = info.get("profitMargins")

      pm_val = round(margin * 100, 1) if margin is not None else None
      de_val = None
      if debt_to_eq is not None:
        de_val = (
            round(debt_to_eq / 100, 2)
            if debt_to_eq > 10
            else round(debt_to_eq, 2)
        )

      corp_sound = (
          (roe_val is not None and roe_val >= 14.0)
          and (de_val is not None and de_val <= 1.2)
          and (pm_val is not None and pm_val >= 8.0)
          and val_pass
      )

      return {
          "sector_type": "CORP",
          "mcap_str": mcap_str,
          "cap_category": cap_category,
          "pe": f"{pe_val}x" if pe_val else "N/A",
          "peg": f"{peg_val}" if peg_val else "N/A",
          "roe": f"{roe_val}%" if roe_val else "N/A",
          "primary_label": "D/E",
          "primary_val": f"{de_val}x" if de_val is not None else "N/A",
          "secondary_label": "Margin",
          "secondary_val": f"{pm_val}%" if pm_val else "N/A",
          "fund_strong": bool(corp_sound),
      }

  except Exception:
    return {
        "sector_type": "CORP",
        "mcap_str": "N/A",
        "cap_category": "Unknown",
        "pe": "N/A",
        "peg": "N/A",
        "roe": "N/A",
        "primary_label": "D/E",
        "primary_val": "N/A",
        "secondary_label": "Margin",
        "secondary_val": "N/A",
        "fund_strong": False,
    }


def run_scan():
  ist = pytz.timezone("Asia/Kolkata")
  timestamp_ist = datetime.now(ist).strftime("%Y-%m-%d %I:%M %p IST")

  matches = []
  all_data = []

  print(f"Scanning {len(WATCHLIST)} stocks with complete metrics...")

  for ticker in WATCHLIST:
    symbol = ticker.replace(".NS", "")
    try:
      t = yf.Ticker(ticker)

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

      above_mas = (curr_price > ema_20.iloc[-1]) and (
          curr_price > ema_50.iloc[-1]
      )
      volume_surge = vol_multiplier >= 1.2
      rsi_valid = 50.0 <= curr_rsi <= 70.0
      near_52w_high = pct_off_52w <= 15.0
      tech_match = bool(
          above_mas and volume_surge and rsi_valid and near_52w_high
      )

      fund = evaluate_company_fundamentals(t, symbol)
      is_match = bool(tech_match and fund["fund_strong"])

      item = {
          "symbol": symbol,
          "price": round(curr_price, 2),
          "high_52w": round(high_52w, 2),
          "pct_off_52w": round(pct_off_52w, 1),
          "vol_surge": round(vol_multiplier, 2),
          "rsi": round(curr_rsi, 1),
          "mcap_str": fund["mcap_str"],
          "cap_category": fund["cap_category"],
          "pe": fund["pe"],
          "peg": fund["peg"],
          "roe": fund["roe"],
          "sector_type": fund["sector_type"],
          "primary_label": fund["primary_label"],
          "primary_val": fund["primary_val"],
          "secondary_label": fund["secondary_label"],
          "secondary_val": fund["secondary_val"],
          "fund_strong": fund["fund_strong"],
          "tech_match": tech_match,
          "matched": is_match,
      }
      all_data.append(item)

      status_label = (
          "[HIGH CONVICTION]"
          if is_match
          else (
              "[FUND STRONG]"
              if fund["fund_strong"]
              else ("[TECH ONLY]" if tech_match else "[-]")
          )
      )
      print(f"{status_label:18} {symbol:12} : {fund['mcap_str']} | P/E {fund['pe']}")

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
      f"\nScan completed at {timestamp_ist}. Total items written:"
      f" {len(all_data)}"
  )


if __name__ == "__main__":
  run_scan()
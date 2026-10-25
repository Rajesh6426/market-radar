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
    # Fundamental Small & Mid-Caps
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


def to_crores_str(val):
  if val is None or pd.isna(val) or val == 0:
    return "N/A"
  cr = round(val / 10000000, 1)
  return f"₹{cr:,.0f} Cr"


def classify_market_cap(mcap_raw):
  if not mcap_raw or mcap_raw <= 0:
    return 0, "N/A", "Cap N/A"
  mcap_cr = round(mcap_raw / 10000000, 1)
  if mcap_cr >= 20000:
    cap_type = "Large-Cap"
  elif mcap_cr >= 5000:
    cap_type = "Mid-Cap"
  else:
    cap_type = "Small-Cap"
  return mcap_cr, f"₹{mcap_cr:,.0f} Cr", cap_type


def parse_pl_table(df, fallback_rev=None, fallback_pat=None):
  periods = []
  if df is None or not isinstance(df, pd.DataFrame) or df.empty:
    return periods

  try:
    cols = list(df.columns)[:4]

    def get_best_row(preferred_keys):
      for target in preferred_keys:
        for idx in df.index:
          s_clean = str(idx).strip().lower()
          if s_clean == target.lower():
            return idx
      for target in preferred_keys:
        for idx in df.index:
          s_clean = str(idx).strip().lower()
          if s_clean.startswith(target.lower()):
            return idx
      return None

    rev_key = get_best_row([
        "Total Revenue",
        "Operating Revenue",
        "TotalRevenue",
        "Interest Income",
    ])
    op_key = get_best_row(
        ["Operating Income", "EBITDA", "EBIT", "Total Operating Income"]
    )
    pat_key = get_best_row([
        "Net Income Common Stockholders",
        "Net Income",
        "Net Income Continuous Operations",
        "Diluted NI",
    ])

    for col in cols:
      label = (
          col.strftime("%b %Y")
          if hasattr(col, "strftime")
          else str(col)[:10]
      )

      rev_val = None
      if rev_key is not None:
        val = df.loc[rev_key, col]
        rev_val = val.iloc[0] if isinstance(val, (pd.Series, list)) else val

      op_val = None
      if op_key is not None:
        val = df.loc[op_key, col]
        op_val = val.iloc[0] if isinstance(val, (pd.Series, list)) else val

      pat_val = None
      if pat_key is not None:
        val = df.loc[pat_key, col]
        pat_val = val.iloc[0] if isinstance(val, (pd.Series, list)) else val

      if rev_val is None and col == cols[0] and fallback_rev:
        rev_val = fallback_rev
      if pat_val is None and col == cols[0] and fallback_pat:
        pat_val = fallback_pat

      margin_str = "N/A"
      try:
        if (
            rev_val is not None
            and pat_val is not None
            and not pd.isna(rev_val)
            and not pd.isna(pat_val)
        ):
          r_f = float(rev_val)
          p_f = float(pat_val)
          if r_f > 0:
            m_val = round((p_f / r_f) * 100, 1)
            if -100 <= m_val <= 100:
              margin_str = f"{m_val}%"
      except Exception:
        pass

      periods.append({
          "period": label,
          "revenue": to_crores_str(rev_val),
          "op_profit": to_crores_str(op_val),
          "pat": to_crores_str(pat_val),
          "margin": margin_str,
          "raw_rev": rev_val,
          "raw_pat": pat_val,
      })
  except Exception as e:
    print(f"Error parsing financial table: {e}")

  return periods


def evaluate_screener_rules(ticker_obj, symbol: str, curr_price: float) -> dict:
  info = ticker_obj.info or {}

  raw_mcap = info.get("marketCap")
  if not raw_mcap:
    try:
      raw_mcap = getattr(ticker_obj.fast_info, "market_cap", None)
    except Exception:
      raw_mcap = None
  mcap_num, mcap_str, cap_category = classify_market_cap(raw_mcap)

  pe = info.get("trailingPE")
  pe_val = round(pe, 1) if pe and pe > 0 else None

  f_pe = info.get("forwardPE")
  f_pe_val = round(f_pe, 1) if f_pe and f_pe > 0 else None

  peg = info.get("pegRatio")
  peg_val = round(peg, 2) if peg and peg > 0 else None

  pb = info.get("priceToBook")
  book_val = info.get("bookValue")
  if (not pb or pb <= 0) and book_val and book_val > 0 and curr_price:
    pb = curr_price / book_val
  pb_val = round(pb, 2) if pb and pb > 0 else None

  roe = info.get("returnOnEquity")
  roe_val = round(roe * 100, 1) if roe is not None else None

  roa = info.get("returnOnAssets")
  roa_val = round(roa * 100, 2) if roa is not None else None

  revenue = info.get("totalRevenue")
  ebitda = info.get("ebitda") or info.get("operatingIncome")
  net_income = info.get("netIncomeToCommon")

  rev_str = to_crores_str(revenue)
  op_str = to_crores_str(ebitda)
  pat_str = to_crores_str(net_income)

  margin = info.get("profitMargins")
  if (margin is None) and revenue and net_income and revenue > 0:
    margin = net_income / revenue
  pm_val = round(margin * 100, 1) if margin is not None else None
  margin_str = f"{pm_val}%" if pm_val is not None else "N/A"

  annual_pl = []
  quarterly_pl = []
  try:
    annual_pl = parse_pl_table(ticker_obj.financials, revenue, net_income)
  except Exception:
    pass

  try:
    quarterly_pl = parse_pl_table(ticker_obj.quarterly_financials)
  except Exception:
    pass

  sales_3y_cagr = None
  pat_3y_cagr = None
  try:
    if len(annual_pl) >= 3:
      latest_r = annual_pl[0].get("raw_rev")
      oldest_r = annual_pl[2].get("raw_rev")
      if latest_r and oldest_r and float(oldest_r) > 0 and float(latest_r) > 0:
        sales_3y_cagr = round(
            (((float(latest_r) / float(oldest_r)) ** (1 / 2)) - 1) * 100, 1
        )

      latest_p = annual_pl[0].get("raw_pat")
      oldest_p = annual_pl[2].get("raw_pat")
      if latest_p and oldest_p and float(oldest_p) > 0 and float(latest_p) > 0:
        pat_3y_cagr = round(
            (((float(latest_p) / float(oldest_p)) ** (1 / 2)) - 1) * 100, 1
        )
  except Exception:
    pass

  total_assets = info.get("totalAssets")
  total_debt = info.get("totalDebt")
  total_cash = info.get("totalCash")

  shares_out = info.get("sharesOutstanding")
  total_equity = None
  if book_val and shares_out:
    total_equity = book_val * shares_out

  if not total_assets and total_equity:
    total_assets = total_equity + (total_debt or 0)

  assets_str = to_crores_str(total_assets)
  equity_str = to_crores_str(total_equity)
  debt_str = to_crores_str(total_debt) if total_debt else "₹0 Cr"
  cash_str = to_crores_str(total_cash)

  debt_to_eq = info.get("debtToEquity")
  de_val = None
  if debt_to_eq is not None:
    de_val = (
        round(debt_to_eq / 100, 2) if debt_to_eq > 10 else round(debt_to_eq, 2)
    )
  elif total_debt is not None and total_equity and total_equity > 0:
    de_val = round(total_debt / total_equity, 2)

  op_inc = info.get("operatingIncome") or ebitda
  int_exp = info.get("interestExpense")
  int_cov = None
  if op_inc and int_exp and float(int_exp) > 0:
    int_cov = round(float(op_inc) / float(int_exp), 1)

  for p in annual_pl:
    p.pop("raw_rev", None)
    p.pop("raw_pat", None)
  for p in quarterly_pl:
    p.pop("raw_rev", None)
    p.pop("raw_pat", None)

  is_finance = symbol in FINANCIAL_STOCKS
  passed_rules = 0
  total_rules = 0
  checks = []

  if is_finance:
    total_rules = 7

    r1 = mcap_num >= 2000
    checks.append(f"M.Cap > ₹2000Cr: {'✓' if r1 else '✗'}")
    if r1:
      passed_rules += 1

    r2 = roa_val is not None and roa_val >= 1.2
    checks.append(f"ROA > 1.2%: {'✓' if r2 else '✗'} ({roa_val}%)")
    if r2:
      passed_rules += 1

    r3 = roe_val is not None and roe_val >= 13.0
    checks.append(f"ROE > 13%: {'✓' if r3 else '✗'} ({roe_val}%)")
    if r3:
      passed_rules += 1

    r4 = pb_val is not None and pb_val <= 2.5
    checks.append(f"P/B < 2.5x: {'✓' if r4 else '✗'} ({pb_val}x)")
    if r4:
      passed_rules += 1

    r5 = (sales_3y_cagr is not None and sales_3y_cagr >= 12.0) or (
        info.get("revenueGrowth", 0) >= 0.10
    )
    checks.append(f"Sales Grw > 12%: {'✓' if r5 else '✗'}")
    if r5:
      passed_rules += 1

    r6 = (pat_3y_cagr is not None and pat_3y_cagr >= 14.0) or (
        info.get("earningsGrowth", 0) >= 0.12
    )
    checks.append(f"PAT Grw > 14%: {'✓' if r6 else '✗'}")
    if r6:
      passed_rules += 1

    r7 = (peg_val is not None and peg_val <= 2.2) or (
        pe_val is not None and pe_val <= 25
    )
    checks.append(f"Valuation OK: {'✓' if r7 else '✗'}")
    if r7:
      passed_rules += 1

    fund_sound = passed_rules >= 5
    sector_type = "BANK/NBFC"
    primary_label, primary_val = "ROA", f"{roa_val}%" if roa_val else "N/A"
    secondary_label, secondary_val = "P/B", f"{pb_val}x" if pb_val else "N/A"
    de_str = "N/A (Bank)"

  else:
    total_rules = 8

    r1 = mcap_num >= 1000
    checks.append(f"M.Cap > ₹1000Cr: {'✓' if r1 else '✗'}")
    if r1:
      passed_rules += 1

    r2 = roe_val is not None and roe_val >= 15.0
    checks.append(f"ROE/ROCE > 15%: {'✓' if r2 else '✗'} ({roe_val}%)")
    if r2:
      passed_rules += 1

    r3 = (de_val is not None and de_val <= 0.5) or (total_debt == 0)
    checks.append(f"D/E < 0.5: {'✓' if r3 else '✗'} ({de_val}x)")
    if r3:
      passed_rules += 1

    r4 = (int_cov is not None and int_cov >= 4.0) or (
        de_val is not None and de_val <= 0.1
    )
    checks.append(f"Int Cov > 4x: {'✓' if r4 else '✗'}")
    if r4:
      passed_rules += 1

    r5 = (sales_3y_cagr is not None and sales_3y_cagr >= 10.0) or (
        info.get("revenueGrowth", 0) >= 0.08
    )
    checks.append(f"Sales Grw > 10%: {'✓' if r5 else '✗'}")
    if r5:
      passed_rules += 1

    r6 = (pat_3y_cagr is not None and pat_3y_cagr >= 12.0) or (
        info.get("earningsGrowth", 0) >= 0.10
    )
    checks.append(f"PAT Grw > 12%: {'✓' if r6 else '✗'}")
    if r6:
      passed_rules += 1

    r7 = pm_val is not None and pm_val >= 10.0
    checks.append(f"Margin > 10%: {'✓' if r7 else '✗'} ({margin_str})")
    if r7:
      passed_rules += 1

    r8 = (peg_val is not None and peg_val <= 2.2) or (
        pe_val is not None and pe_val <= 42
    )
    checks.append(f"Valuation OK: {'✓' if r8 else '✗'}")
    if r8:
      passed_rules += 1

    fund_sound = passed_rules >= 6
    sector_type = "CORPORATE"
    de_str = f"{de_val}x" if de_val is not None else "N/A"
    primary_label, primary_val = "D/E", de_str
    secondary_label, secondary_val = "Margin", margin_str

  score_str = f"{passed_rules}/{total_rules}"

  return {
      "mcap_str": mcap_str,
      "cap_category": cap_category,
      "sector_type": sector_type,
      "screener_score": score_str,
      "passed_rules": passed_rules,
      "total_rules": total_rules,
      "screener_passed": fund_sound,
      "checks": checks,
      "pe": f"{pe_val}x" if pe_val else "N/A",
      "forward_pe": f"{f_pe_val}x" if f_pe_val else "N/A",
      "peg": f"{peg_val}" if peg_val else "N/A",
      "pb": f"{pb_val}x" if pb_val else "N/A",
      "roe": f"{roe_val}%" if roe_val else "N/A",
      "roa": f"{roa_val}%" if roa_val else "N/A",
      "de": de_str,
      "primary_label": primary_label,
      "primary_val": primary_val,
      "secondary_label": secondary_label,
      "secondary_val": secondary_val,
      "revenue": rev_str,
      "op_profit": op_str,
      "pat": pat_str,
      "net_margin": margin_str,
      "annual_pl": annual_pl,
      "quarterly_pl": quarterly_pl,
      "total_assets": assets_str,
      "total_equity": equity_str,
      "total_debt": debt_str,
      "cash": cash_str,
  }


def run_scan():
  ist = pytz.timezone("Asia/Kolkata")
  timestamp_ist = datetime.now(ist).strftime("%Y-%m-%d %I:%M %p IST")

  matches = []
  all_data = []

  print(
      f"Scanning {len(WATCHLIST)} symbols using Institutional Screener Rules..."
  )

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

      fund = evaluate_screener_rules(t, symbol, curr_price)

      full_conviction = bool(tech_match and fund.get("screener_passed", False))

      if full_conviction:
        conviction_tag = "INSTITUTIONAL BUY"
        badge_type = "badge-match"
      elif fund.get("screener_passed", False):
        conviction_tag = "QUALITY COMPOUNDER"
        badge_type = "badge-fund-good"
      elif tech_match:
        conviction_tag = "MOMENTUM ONLY"
        badge_type = "badge-momentum"
      else:
        conviction_tag = "NEUTRAL"
        badge_type = "badge-neutral"

      item = {
          "symbol": symbol,
          "price": round(curr_price, 2),
          "high_52w": round(high_52w, 2),
          "pct_off_52w": round(pct_off_52w, 1),
          "vol_surge": round(vol_multiplier, 2),
          "rsi": round(curr_rsi, 1),
          "tech_match": tech_match,
          "matched": full_conviction,
          "conviction_tag": conviction_tag,
          "badge_type": badge_type,
          **fund,
      }
      all_data.append(item)
      if full_conviction:
        matches.append(item)

      print(
          f"[{conviction_tag:18}] {symbol:10} | Sector: {item['sector_type']:10}"
          f" | Score: {item['screener_score']}"
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

  print(f"\nScan completed at {timestamp_ist}. Total items: {len(all_data)}")


if __name__ == "__main__":
  run_scan()
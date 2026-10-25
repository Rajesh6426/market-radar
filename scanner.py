import json
import time
from datetime import datetime
import numpy as np
import pandas as pd
import pytz
import yfinance as yf

# Broad Financials list for dual-engine sector isolation
FINANCIAL_STOCKS = {
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "AXISBANK",
    "KOTAKBANK",
    "BAJFINANCE",
    "BAJAJFINSV",
    "CHOLAFIN",
    "SHRIRAMFIN",
    "MUTHOOTFIN",
    "BANKBARODA",
    "CANBK",
    "PNB",
    "INDUSINDBK",
    "FEDERALBNK",
    "IDFCFIRSTB",
    "AUBANK",
    "BANDHANBNK",
    "POONAWALLA",
    "M&MFIN",
    "LICHSGFIN",
    "MANAPPURAM",
    "SBICARD",
    "HDFCAMC",
    "NAM-INDIA",
}

# Complete Nifty 500 Liquid Ticker Universe
NIFTY_500_SYMBOLS = [
    "360ONE",
    "3MINDIA",
    "ABB",
    "ACC",
    "AIAENG",
    "APLAPOLLO",
    "AUBANK",
    "AARTIDRUGS",
    "AARTIIND",
    "AAVAS",
    "ABBOTINDIA",
    "ACE",
    "ADANIENSOL",
    "ADANIENT",
    "ADANIGREEN",
    "ADANIPORTS",
    "ADANIPOWER",
    "AFFLE",
    "AJANTPHARM",
    "ALKEM",
    "ALOKINDS",
    "AMBER",
    "AMBUJACEM",
    "ANANDRATHI",
    "ANGELONE",
    "APARINDS",
    "APOLLOHOSP",
    "APOLLOTYRE",
    "APTUS",
    "ARE&M",
    "ASHOKLEY",
    "ASIANPAINT",
    "ASTERDM",
    "ASTRAL",
    "ATGL",
    "ATUL",
    "AUROPHARMA",
    "AVANTIFEED",
    "AXISBANK",
    "BAJAJ-AUTO",
    "BAJAJFINSV",
    "BAJAJHLDNG",
    "BAJFINANCE",
    "BALAMINES",
    "BALKRISIND",
    "BALRAMCHIN",
    "BANDHANBNK",
    "BANKBARODA",
    "BANKINDIA",
    "BATAINDIA",
    "BAYERCROP",
    "BERGEPAINT",
    "BDL",
    "BEL",
    "BEML",
    "BHARATFORG",
    "BHARTIARTL",
    "BHEL",
    "BIOCON",
    "BIRLACORPN",
    "BLS",
    "BLUEDART",
    "BLUESTARCO",
    "BOSCHLTD",
    "BPCL",
    "BRIGADE",
    "BRITANNIA",
    "BSOFT",
    "CAMPUS",
    "CANFINHOME",
    "CANBK",
    "CAPL",
    "CARBORUNIV",
    "CASTROLIND",
    "CEATLTD",
    "CENTRALBK",
    "CDSL",
    "CENTURYPLY",
    "CENTURYTEX",
    "CERA",
    "CESC",
    "CGPOWER",
    "CHALET",
    "CHAMBLFERT",
    "CHEMPLASTS",
    "CHOLAHLDNG",
    "CHOLAFIN",
    "CIPLA",
    "CLEAN",
    "COALINDIA",
    "COCHINSHIP",
    "COFORGE",
    "COLPAL",
    "CONCOR",
    "COROMANDEL",
    "CRAFTSMAN",
    "CREDITACC",
    "CROMPTON",
    "CUMMINSIND",
    "CYIENT",
    "DABUR",
    "DALBHARAT",
    "DEEPAKNTR",
    "DELHIVERY",
    "DEVYANI",
    "DIVISLAB",
    "DIXON",
    "DLF",
    "DMART",
    "DRREDDY",
    "EIDPARRY",
    "EIHOTEL",
    "EPL",
    "EICHERMOT",
    "ELECON",
    "ELGIEQUIP",
    "EMAMILTD",
    "ENDURANCE",
    "ENGINERSIN",
    "EQUITASBNK",
    "ERIS",
    "ESCORTS",
    "EXIDEIND",
    "FDC",
    "FEDERALBNK",
    "FACT",
    "FINEORG",
    "FINCABLES",
    "FINPIPE",
    "FSL",
    "FORTIS",
    "GAIL",
    "GMRINFRA",
    "GLENMARK",
    "GODFRYPHLP",
    "GODREJCP",
    "GODREJIND",
    "GODREJPROP",
    "GRANULES",
    "GRASIM",
    "GRAVITA",
    "GESHIP",
    "GRINDWELL",
    "GUJGASLTD",
    "GNFC",
    "GPPL",
    "GSPL",
    "HAVELLS",
    "HCLTECH",
    "HDFCAMC",
    "HDFCBANK",
    "HDFCLIFE",
    "HEROMOTOCO",
    "HFCL",
    "HINDALCO",
    "HINDCOPPER",
    "HINDPETRO",
    "HINDUNILVR",
    "HINDZINC",
    "HONAUT",
    "HUDCO",
    "ICICIBANK",
    "ICICIGI",
    "ICICIPRULI",
    "IEX",
    "INDIACEM",
    "INDIAMART",
    "INDIANB",
    "INDHOTEL",
    "IOC",
    "IOB",
    "IRCTC",
    "IRFC",
    "IREDA",
    "IGL",
    "INDUSINDBK",
    "INDUSTOWER",
    "INFY",
    "INOXWIND",
    "INTELLECT",
    "INDIGO",
    "IPCALAB",
    "ITC",
    "ITI",
    "J&KBANK",
    "JBCHEPHARM",
    "JKCEMENT",
    "JKLAKSHMI",
    "JKPAPER",
    "JMFINANCIL",
    "JSWENERGY",
    "JSWINFRA",
    "JSWSTEEL",
    "JSL",
    "JUBLFOOD",
    "JUBLINGREA",
    "JUBLPHARMA",
    "JUSTDIAL",
    "JYOTHYLAB",
    "KALYANKJIL",
    "KANSAINER",
    "KARURVYSYA",
    "KEC",
    "KEI",
    "KFINTECH",
    "KIRLOSENG",
    "KOTAKBANK",
    "KPITTECH",
    "KPRMILL",
    "KRBL",
    "KSB",
    "L&TFH",
    "LT",
    "LTIM",
    "LTTS",
    "LAURUSLABS",
    "LICHSGFIN",
    "LICI",
    "LINDEINDIA",
    "LUPIN",
    "MMTC",
    "MRF",
    "MGL",
    "MAHSCOOTER",
    "MAHSEAMLES",
    "M&MFIN",
    "M&M",
    "MANAPPURAM",
    "MARICO",
    "MARUTI",
    "MASTEK",
    "MAXHEALTH",
    "MAZDOCK",
    "MEDANTA",
    "METROPOLIS",
    "MFSL",
    "MPHASIS",
    "MRPL",
    "MUTHOOTFIN",
    "NATCOPHARM",
    "NATIONALUM",
    "NAVINFLUOR",
    "NBCC",
    "NCC",
    "NHPC",
    "NLCINDIA",
    "NMDC",
    "NTPC",
    "NH",
    "NATIONALUM",
    "NAUKRI",
    "NESCO",
    "NETWORK18",
    "NIPPON",
    "OBEROIRLTY",
    "OFSS",
    "OIL",
    "OLECTRA",
    "PAYTM",
    "PERSISTENT",
    "PETRONET",
    "PFC",
    "PFIZER",
    "PGHH",
    "PHOENIXLTD",
    "PIDILITIND",
    "PIIND",
    "PNB",
    "POLICYBZR",
    "POLYCAB",
    "PPLPHARMA",
    "PRESTIGE",
    "RADICO",
    "RVNL",
    "RAILTEL",
    "RAINBOW",
    "RAJESHEXPO",
    "RBLBANK",
    "REC",
    "RELIANCE",
    "RITES",
    "SAIL",
    "SBICARD",
    "SBILIFE",
    "SBIN",
    "SHREECEM",
    "SHRIRAMFIN",
    "SIEMENS",
    "SJVN",
    "SOBHA",
    "SOLARINDS",
    "SONACOMS",
    "STARHEALTH",
    "SUNPHARMA",
    "SUNTV",
    "SUNDARMFIN",
    "SUZLON",
    "SWANENERGY",
    "TATACHEM",
    "TATACOMM",
    "TATACONSUM",
    "TATAELXSI",
    "TATAMOTORS",
    "TATAPOWER",
    "TATASTEEL",
    "TATATECH",
    "TCS",
    "TECHM",
    "TEJASNET",
    "THERMAX",
    "TIMKEN",
    "TITAGARH",
    "TITAN",
    "TORNTPHARM",
    "TORNTPOWER",
    "TRENT",
    "TRIDENT",
    "TRITURBINE",
    "TIINDIA",
    "UCOBANK",
    "UNOMINDA",
    "UPL",
    "UTIAMC",
    "ULTRACEMCO",
    "UNIONBANK",
    "VGUARD",
    "VMART",
    "VIPIND",
    "VOLTAS",
    "WARBURTON",
    "WELCORP",
    "WELSPUNLIV",
    "WESTLIFE",
    "WHIRLPOOL",
    "WIPRO",
    "YESBANK",
    "ZEEENT",
    "ZENSARTECH",
    "ZYDUSLIFE",
    "ZYDUSWELL",
]


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


def evaluate_fundamentals(ticker_obj, symbol: str, curr_price: float) -> dict:
  info = {}
  try:
    info = ticker_obj.info or {}
  except Exception:
    pass

  raw_mcap = info.get("marketCap")
  if not raw_mcap:
    try:
      raw_mcap = getattr(ticker_obj.fast_info, "market_cap", None)
    except Exception:
      raw_mcap = None

  mcap_cr = round(raw_mcap / 10000000, 1) if raw_mcap else 0
  mcap_str = f"₹{mcap_cr:,.0f} Cr" if mcap_cr > 0 else "N/A"
  cap_category = (
      "Large-Cap"
      if mcap_cr >= 20000
      else ("Mid-Cap" if mcap_cr >= 5000 else "Small-Cap")
  )

  pe = info.get("trailingPE")
  pe_val = round(pe, 1) if pe and pe > 0 else None

  pb = info.get("priceToBook")
  book_val = info.get("bookValue")
  if (not pb or pb <= 0) and book_val and book_val > 0 and curr_price:
    pb = curr_price / book_val
  pb_val = round(pb, 2) if pb and pb > 0 else None

  peg = info.get("pegRatio")
  peg_val = round(peg, 2) if peg and peg > 0 else None

  roa = info.get("returnOnAssets")
  roa_val = round(roa * 100, 2) if roa is not None else None

  revenue = info.get("totalRevenue")
  net_income = info.get("netIncomeToCommon")
  total_debt = info.get("totalDebt")
  shares_out = info.get("sharesOutstanding")

  total_equity = None
  if book_val and shares_out:
    total_equity = book_val * shares_out

  roe = info.get("returnOnEquity")
  roe_val = round(roe * 100, 1) if roe is not None else None
  if roe_val is None and net_income and total_equity and total_equity > 0:
    roe_val = round((net_income / total_equity) * 100, 1)

  margin = info.get("profitMargins")
  if (margin is None) and revenue and net_income and revenue > 0:
    margin = net_income / revenue
  pm_val = round(margin * 100, 1) if margin is not None else None
  margin_str = f"{pm_val}%" if pm_val is not None else "N/A"

  debt_to_eq = info.get("debtToEquity")
  de_val = None
  if debt_to_eq is not None:
    de_val = (
        round(debt_to_eq / 100, 2) if debt_to_eq > 1.5 else round(debt_to_eq, 2)
    )
  elif total_debt is not None and total_equity and total_equity > 0:
    de_val = round(total_debt / total_equity, 2)

  is_finance = symbol in FINANCIAL_STOCKS
  passed_rules = 0
  total_rules = 4

  if is_finance:
    sector_type = "BANK/NBFC"
    de_str = "N/A (Bank)"
    if roa_val is not None and roa_val >= 1.1:
      passed_rules += 1
    if roe_val is not None and roe_val >= 13.0:
      passed_rules += 1
    if pb_val is not None and pb_val <= 2.5:
      passed_rules += 1
    if pm_val is not None and pm_val >= 15.0:
      passed_rules += 1
  else:
    sector_type = "CORPORATE"
    de_str = f"{de_val}x" if de_val is not None else "0.00x"
    if (de_val is not None and de_val <= 0.6) or (total_debt == 0):
      passed_rules += 1
    if roe_val is not None and roe_val >= 14.0:
      passed_rules += 1
    if pm_val is not None and pm_val >= 10.0:
      passed_rules += 1
    if (peg_val is not None and peg_val <= 2.2) or (
        pe_val is not None and pe_val <= 42
    ):
      passed_rules += 1

  return {
      "mcap_str": mcap_str,
      "cap_category": cap_category,
      "sector_type": sector_type,
      "pe": f"{pe_val}x" if pe_val else "N/A",
      "peg": f"{peg_val}" if peg_val else "N/A",
      "pb": f"{pb_val}x" if pb_val else "N/A",
      "roe": f"{roe_val}%" if roe_val else "N/A",
      "roa": f"{roa_val}%" if roa_val else "N/A",
      "de": de_str,
      "revenue": to_crores_str(revenue),
      "pat": to_crores_str(net_income),
      "net_margin": margin_str,
      "total_debt": to_crores_str(total_debt) if total_debt else "₹0 Cr",
      "passed_rules": passed_rules,
  }


def run_nifty500_scan():
  ist = pytz.timezone("Asia/Kolkata")
  timestamp_ist = datetime.now(ist).strftime("%Y-%m-%d %I:%M %p IST")

  symbols = [f"{s}.NS" for s in NIFTY_500_SYMBOLS]
  total_symbols = len(symbols)
  print(f"🚀 Starting fast-batch scan across Nifty 500 ({total_symbols} stocks)...")

  chunk_size = 50
  all_data = []
  matches = []

  # Process in 50-stock chunks to download 1Y candles rapidly without hitting Yahoo rate limits
  for i in range(0, total_symbols, chunk_size):
    chunk = symbols[i : i + chunk_size]
    print(
        f"Downloading Technicals batch {i//chunk_size + 1}/{(total_symbols // chunk_size) + 1}..."
    )

    try:
      data = yf.download(
          chunk,
          period="1y",
          interval="1d",
          auto_adjust=True,
          group_by="ticker",
          threads=True,
          progress=False,
      )
    except Exception as e:
      print(f"Batch download error: {e}")
      continue

    for full_ticker in chunk:
      symbol = full_ticker.replace(".NS", "")
      try:
        if full_ticker not in data:
          continue

        df = data[full_ticker].dropna()
        if df.empty or len(df) < 50:
          continue

        close = df["Close"]
        high = df["High"]
        volume = df["Volume"]

        curr_price = float(close.iloc[-1])
        curr_vol = float(volume.iloc[-1])
        avg_vol_20 = float(volume.iloc[-21:-1].mean())
        vol_multiplier = curr_vol / avg_vol_20 if avg_vol_20 > 0 else 0.0

        ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        ema_50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
        rsi_val = float(calculate_rsi(close).iloc[-1])

        high_52w = float(high.max())
        pct_off_52w = ((high_52w - curr_price) / high_52w) * 100.0

        above_mas = (curr_price > ema_20) and (curr_price > ema_50)
        volume_surge = vol_multiplier >= 1.15
        rsi_valid = 48.0 <= rsi_val <= 72.0
        near_52w_high = pct_off_52w <= 15.0

        tech_match = bool(
            above_mas and volume_surge and rsi_valid and near_52w_high
        )

        # Pull fundamentals
        t = yf.Ticker(full_ticker)
        fund = evaluate_fundamentals(t, symbol, curr_price)

        # Recommendation: BUY, WAIT, or SELL
        if tech_match and fund["passed_rules"] >= 3:
          conviction_tag = "BUY"
          badge_type = "rec-buy"
        elif fund["passed_rules"] >= 2:
          conviction_tag = "WAIT"
          badge_type = "rec-wait"
        else:
          conviction_tag = "SELL"
          badge_type = "rec-sell"

        stock_item = {
            "symbol": symbol,
            "price": round(curr_price, 2),
            "high_52w": round(high_52w, 2),
            "pct_off_52w": round(pct_off_52w, 1),
            "vol_surge": round(vol_multiplier, 2),
            "rsi": round(rsi_val, 1),
            "tech_match": tech_match,
            "conviction_tag": conviction_tag,
            "badge_type": badge_type,
            **fund,
        }

        all_data.append(stock_item)
        if conviction_tag == "BUY":
          matches.append(stock_item)

      except Exception as e:
        continue

    time.sleep(0.5)

  # Sort so that BUY setups appear first at the top of the dashboard, followed by WAIT, then SELL
  sort_order = {"BUY": 0, "WAIT": 1, "SELL": 2}
  all_data.sort(key=lambda x: sort_order.get(x["conviction_tag"], 3))

  payload = {
      "last_updated": timestamp_ist,
      "total_scanned": len(all_data),
      "match_count": len(matches),
      "matches": matches,
      "all_scanned": all_data,
  }

  with open("results.json", "w") as f:
    json.dump(payload, f, indent=2)

  print(
      f"\n✅ Scan finished at {timestamp_ist}. Scanned {len(all_data)} stocks."
  )
  print(f"🔥 Found {len(matches)} active BUY recommendations across Nifty 500!")


if __name__ == "__main__":
  run_nifty500_scan()
import yfinance as yf
import pandas as pd
import json
from datetime import datetime
import pytz

WATCHLIST = [
    # Large-Cap Core
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "BHARTIARTL.NS", "LT.NS", "SBIN.NS", "AXISBANK.NS", "TITAN.NS",
    "ITC.NS", "SUNPHARMA.NS", "MARUTI.NS", "BAJFINANCE.NS",
    # Fundamental Small-Caps
    "CAMS.NS", "NESCO.NS", "CLEAN.NS", "IONEXCHANG.NS", "CASTROLIND.NS"
]

FINANCIAL_STOCKS = ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "BAJFINANCE"]

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss
    return 100.0 - (100.0 / (1.0 + rs))

def to_crores_str(val):
    if val is None or pd.isna(val):
        return "N/A"
    cr = round(val / 10000000, 1)
    return f"₹{cr:,.0f} Cr"

def classify_market_cap(mcap_raw):
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

def extract_financials(ticker_obj, symbol: str) -> dict:
    info = ticker_obj.info or {}
    
    # 1. Market Cap & Valuation
    raw_mcap = info.get('marketCap')
    if not raw_mcap:
        try:
            raw_mcap = getattr(ticker_obj.fast_info, 'market_cap', None)
        except Exception:
            raw_mcap = None
    mcap_str, cap_category = classify_market_cap(raw_mcap)

    pe = info.get('trailingPE') or info.get('forwardPE')
    pe_val = round(pe, 1) if pe and pe > 0 else None
    
    forward_pe = info.get('forwardPE')
    f_pe_val = round(forward_pe, 1) if forward_pe and forward_pe > 0 else None

    peg = info.get('pegRatio')
    peg_val = round(peg, 2) if peg and peg > 0 else None

    pb = info.get('priceToBook')
    pb_val = round(pb, 2) if pb and pb > 0 else None

    roe = info.get('returnOnEquity')
    roe_val = round(roe * 100, 1) if roe is not None else None

    roa = info.get('returnOnAssets')
    roa_val = round(roa * 100, 2) if roa is not None else None

    # 2. Extract P&L items from financial statements
    rev_str, op_str, pat_str, margin_str = "N/A", "N/A", "N/A", "N/A"
    try:
        fin = ticker_obj.financials
        if fin is not None and not fin.empty:
            # Revenue
            rev_keys = [k for k in fin.index if "Revenue" in str(k) or "Interest Income" in str(k)]
            if rev_keys:
                rev_str = to_crores_str(fin.loc[rev_keys[0]].iloc[0])
            
            # Operating Income / EBITDA
            op_keys = [k for k in fin.index if "Operating Income" in str(k) or "EBITDA" in str(k)]
            if op_keys:
                op_str = to_crores_str(fin.loc[op_keys[0]].iloc[0])

            # Net Income (PAT)
            net_keys = [k for k in fin.index if "Net Income" in str(k)]
            if net_keys:
                pat_str = to_crores_str(fin.loc[net_keys[0]].iloc[0])
    except Exception:
        pass

    margin = info.get('profitMargins')
    pm_val = round(margin * 100, 1) if margin is not None else None
    margin_str = f"{pm_val}%" if pm_val is not None else "N/A"

    # 3. Extract Balance Sheet items
    assets_str, equity_str, debt_str, cash_str = "N/A", "N/A", "N/A", "N/A"
    try:
        bs = ticker_obj.balance_sheet
        if bs is not None and not bs.empty:
            # Total Assets
            asset_keys = [k for k in bs.index if "Total Assets" in str(k)]
            if asset_keys:
                assets_str = to_crores_str(bs.loc[asset_keys[0]].iloc[0])

            # Total Equity
            eq_keys = [k for k in bs.index if "Stockholders Equity" in str(k) or "Total Equity" in str(k)]
            if eq_keys:
                equity_str = to_crores_str(bs.loc[eq_keys[0]].iloc[0])

            # Total Debt
            debt_keys = [k for k in bs.index if "Total Debt" in str(k)]
            if debt_keys:
                debt_str = to_crores_str(bs.loc[debt_keys[0]].iloc[0])

            # Cash
            cash_keys = [k for k in bs.index if "Cash And Cash Equivalents" in str(k)]
            if cash_keys:
                cash_str = to_crores_str(bs.loc[cash_keys[0]].iloc[0])
    except Exception:
        pass

    debt_to_eq = info.get('debtToEquity')
    de_val = None
    if debt_to_eq is not None:
        de_val = round(debt_to_eq / 100, 2) if debt_to_eq > 10 else round(debt_to_eq, 2)

    val_pass = (peg_val is not None and peg_val <= 2.5) or (pe_val is not None and pe_val <= 50)

    if symbol in FINANCIAL_STOCKS:
        bank_sound = (roa_val is not None and roa_val >= 1.0) and (roe_val is not None and roe_val >= 12.0) and val_pass
        fund_sound = bool(bank_sound)
        p_label, p_val = "ROA", f"{roa_val}%" if roa_val else "N/A"
        s_label, s_val = "P/B", f"{pb_val}x" if pb_val else "N/A"
    else:
        corp_sound = (roe_val is not None and roe_val >= 14.0) and (de_val is not None and de_val <= 1.2) and (pm_val is not None and pm_val >= 8.0) and val_pass
        fund_sound = bool(corp_sound)
        p_label, p_val = "D/E", f"{de_val}x" if de_val is not None else "N/A"
        s_label, s_val = "Margin", margin_str

    return {
        "mcap_str": mcap_str,
        "cap_category": cap_category,
        "pe": f"{pe_val}x" if pe_val else "N/A",
        "forward_pe": f"{f_pe_val}x" if f_pe_val else "N/A",
        "peg": f"{peg_val}" if peg_val else "N/A",
        "pb": f"{pb_val}x" if pb_val else "N/A",
        "roe": f"{roe_val}%" if roe_val else "N/A",
        "roa": f"{roa_val}%" if roa_val else "N/A",
        "de": f"{de_val}x" if de_val is not None else "N/A",
        "primary_label": p_label,
        "primary_val": p_val,
        "secondary_label": s_label,
        "secondary_val": s_val,
        "fund_strong": fund_sound,
        # P&L Data
        "revenue": rev_str,
        "op_profit": op_str,
        "pat": pat_str,
        "net_margin": margin_str,
        # Balance Sheet Data
        "total_assets": assets_str,
        "total_equity": equity_str,
        "total_debt": debt_str,
        "cash": cash_str
    }

def run_scan():
    ist = pytz.timezone('Asia/Kolkata')
    timestamp_ist = datetime.now(ist).strftime("%Y-%m-%d %I:%M %p IST")
    
    matches = []
    all_data = []

    print(f"Scanning {len(WATCHLIST)} stocks with P&L, Balance Sheet, and Ratios...")

    for ticker in WATCHLIST:
        symbol = ticker.replace(".NS", "")
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="1y", interval="1d", auto_adjust=True)
            if df.empty or len(df) < 50:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]

            close = df['Close']
            high = df['High']
            volume = df['Volume']

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

            above_mas = (curr_price > ema_20.iloc[-1]) and (curr_price > ema_50.iloc[-1])
            volume_surge = vol_multiplier >= 1.2
            rsi_valid = 50.0 <= curr_rsi <= 70.0
            near_52w_high = pct_off_52w <= 15.0
            tech_match = bool(above_mas and volume_surge and rsi_valid and near_52w_high)

            fund = extract_financials(t, symbol)
            is_match = bool(tech_match and fund["fund_strong"])

            item = {
                "symbol": symbol,
                "price": round(curr_price, 2),
                "high_52w": round(high_52w, 2),
                "pct_off_52w": round(pct_off_52w, 1),
                "vol_surge": round(vol_multiplier, 2),
                "rsi": round(curr_rsi, 1),
                "tech_match": tech_match,
                "matched": is_match,
                **fund
            }
            all_data.append(item)
            print(f"[✓] Processed {symbol:12}: Sales {fund['revenue']} | PAT {fund['pat']} | Assets {fund['total_assets']}")

        except Exception as e:
            print(f"[!] Error on {symbol}: {e}")
            continue

    payload = {
        "last_updated": timestamp_ist,
        "total_scanned": len(WATCHLIST),
        "match_count": len(matches),
        "matches": [d for d in all_data if d["matched"]],
        "all_scanned": all_data
    }

    with open("results.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\nScan completed at {timestamp_ist}. Ready for deployment.")

if __name__ == "__main__":
    run_scan()
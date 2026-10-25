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
    if val is None or pd.isna(val) or val == 0:
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

def parse_pl_table(df):
    """Parses a financials DataFrame into a list of period objects (Revenue, EBITDA, PAT, Margin)."""
    periods = []
    if df is None or df.empty:
        return periods

    cols = list(df.columns)[:4]  # Up to 4 most recent periods
    for col in cols:
        label = col.strftime('%b %Y') if hasattr(col, 'strftime') else str(col)[:10]

        # 1. Total Revenue
        rev = None
        rev_keys = [k for k in df.index if "Total Revenue" in str(k) or "Operating Revenue" in str(k) or "Interest Income" in str(k)]
        if rev_keys:
            rev = df.loc[rev_keys[0], col]
            if isinstance(rev, pd.Series):
                rev = rev.iloc[0]

        # 2. Operating Profit / EBITDA
        ebitda = None
        eb_keys = [k for k in df.index if "EBITDA" in str(k) or "Operating Income" in str(k)]
        if eb_keys:
            ebitda = df.loc[eb_keys[0], col]
            if isinstance(ebitda, pd.Series):
                ebitda = ebitda.iloc[0]

        # 3. Net Income (PAT)
        pat = None
        pat_keys = [k for k in df.index if "Net Income Common Stockholders" in str(k) or "Net Income" in str(k)]
        if pat_keys:
            pat = df.loc[pat_keys[0], col]
            if isinstance(pat, pd.Series):
                pat = pat.iloc[0]

        # 4. Margin
        margin_str = "N/A"
        try:
            if rev and pat and float(rev) > 0:
                m_val = round((float(pat) / float(rev)) * 100, 1)
                margin_str = f"{m_val}%"
        except Exception:
            pass

        periods.append({
            "period": label,
            "revenue": to_crores_str(rev),
            "op_profit": to_crores_str(ebitda),
            "pat": to_crores_str(pat),
            "margin": margin_str
        })
    return periods

def extract_financials(ticker_obj, symbol: str, curr_price: float) -> dict:
    info = ticker_obj.info or {}

    raw_mcap = info.get('marketCap')
    if not raw_mcap:
        try:
            raw_mcap = getattr(ticker_obj.fast_info, 'market_cap', None)
        except Exception:
            raw_mcap = None
    mcap_str, cap_category = classify_market_cap(raw_mcap)

    pe = info.get('trailingPE')
    pe_val = round(pe, 1) if pe and pe > 0 else None
    
    f_pe = info.get('forwardPE')
    f_pe_val = round(f_pe, 1) if f_pe and f_pe > 0 else None

    peg = info.get('pegRatio')
    peg_val = round(peg, 2) if peg and peg > 0 else None

    pb = info.get('priceToBook')
    book_val = info.get('bookValue')
    if (not pb or pb <= 0) and book_val and book_val > 0 and curr_price:
        pb = curr_price / book_val
    pb_val = round(pb, 2) if pb and pb > 0 else None

    roe = info.get('returnOnEquity')
    roe_val = round(roe * 100, 1) if roe is not None else None

    roa = info.get('returnOnAssets')
    roa_val = round(roa * 100, 2) if roa is not None else None

    # TTM headline numbers
    revenue = info.get('totalRevenue')
    ebitda = info.get('ebitda') or info.get('operatingIncome')
    net_income = info.get('netIncomeToCommon')

    rev_str = to_crores_str(revenue)
    op_str = to_crores_str(ebitda)
    pat_str = to_crores_str(net_income)

    margin = info.get('profitMargins')
    if (margin is None) and revenue and net_income and revenue > 0:
        margin = net_income / revenue
    pm_val = round(margin * 100, 1) if margin is not None else None
    margin_str = f"{pm_val}%" if pm_val is not None else "N/A"

    # Multi-period P&L extraction
    annual_pl = []
    quarterly_pl = []
    try:
        annual_pl = parse_pl_table(ticker_obj.financials)
    except Exception:
        pass

    try:
        quarterly_pl = parse_pl_table(ticker_obj.quarterly_financials)
    except Exception:
        pass

    # Balance Sheet summary
    total_assets = info.get('totalAssets')
    total_debt = info.get('totalDebt')
    total_cash = info.get('totalCash')

    shares_out = info.get('sharesOutstanding')
    total_equity = None
    if book_val and shares_out:
        total_equity = book_val * shares_out

    if not total_assets and total_equity:
        total_assets = total_equity + (total_debt or 0)

    assets_str = to_crores_str(total_assets)
    equity_str = to_crores_str(total_equity)
    debt_str = to_crores_str(total_debt) if total_debt else "₹0 Cr"
    cash_str = to_crores_str(total_cash)

    debt_to_eq = info.get('debtToEquity')
    de_val = None
    if debt_to_eq is not None:
        de_val = round(debt_to_eq / 100, 2) if debt_to_eq > 10 else round(debt_to_eq, 2)
    elif total_debt is not None and total_equity and total_equity > 0:
        de_val = round(total_debt / total_equity, 2)

    de_str = f"{de_val}x" if de_val is not None else "N/A"

    val_pass = (peg_val is not None and peg_val <= 2.5) or (pe_val is not None and pe_val <= 50)

    if symbol in FINANCIAL_STOCKS:
        bank_sound = (roa_val is not None and roa_val >= 0.9) and (roe_val is not None and roe_val >= 11.0) and val_pass
        fund_sound = bool(bank_sound)
        p_label, p_val = "ROA", f"{roa_val}%" if roa_val else "N/A"
        s_label, s_val = "P/B", f"{pb_val}x" if pb_val else "N/A"
        de_str = "N/A (Bank)"
    else:
        corp_sound = (roe_val is not None and roe_val >= 14.0) and (de_val is not None and de_val <= 1.2) and (pm_val is not None and pm_val >= 8.0) and val_pass
        fund_sound = bool(corp_sound)
        p_label, p_val = "D/E", de_str
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
        "de": de_str,
        "primary_label": p_label,
        "primary_val": p_val,
        "secondary_label": s_label,
        "secondary_val": s_val,
        "fund_strong": fund_sound,
        "revenue": rev_str,
        "op_profit": op_str,
        "pat": pat_str,
        "net_margin": margin_str,
        "annual_pl": annual_pl,
        "quarterly_pl": quarterly_pl,
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

    print(f"Scanning {len(WATCHLIST)} symbols for Multi-Year & Quarterly Statements...")

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

            fund = extract_financials(t, symbol, curr_price)
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
            if is_match:
                matches.append(item)

            print(f"[✓] {symbol:10} | Annual Periods: {len(fund['annual_pl'])} | Quarterly Periods: {len(fund['quarterly_pl'])}")

        except Exception as e:
            print(f"[!] Error on {symbol}: {e}")
            continue

    payload = {
        "last_updated": timestamp_ist,
        "total_scanned": len(WATCHLIST),
        "match_count": len(matches),
        "matches": matches,
        "all_scanned": all_data
    }

    with open("results.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\nScan complete at {timestamp_ist}.")

if __name__ == "__main__":
    run_scan()
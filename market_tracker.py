import os
import time
import requests
from datetime import datetime, timezone, timedelta

# =====================================================================
# CONFIGURATION & CREDENTIALS
# =====================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8847366387:AAFFnPjhzAwJSN-pzdi0PvxGrL0xYVQZGug")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5432795318")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "91493d50f9msh678320be277a9e4p16aa0bjsn0532d5a9583c")
RAPIDAPI_HOST = "irctc-indian-railway-pnr-status.p.rapidapi.com"

IST_OFFSET = timedelta(hours=5, minutes=30)

# Memory storage for tracked PNRs: { "pnr_number": "last_status_summary" }
tracked_pnrs = {}

# =====================================================================
# TIME & TELEGRAM DISPATCHERS
# =====================================================================
def get_ist_now():
    """Returns the current datetime in Indian Standard Time (IST)."""
    return datetime.now(timezone.utc) + IST_OFFSET

def send_telegram(message: str):
    """Sends a markdown-formatted message to the designated Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to dispatch Telegram alert: {e}")
        return False

# =====================================================================
# IRCTC PNR TRACKING ENGINE
# =====================================================================
def get_pnr_status(pnr: str):
    """Queries RapidAPI for real-time IRCTC PNR details."""
    url = f"https://{RAPIDAPI_HOST}/getPNRStatus/{pnr}"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data.get("success") and "data" in data:
                return data["data"]
            elif "data" in data:
                return data["data"]
            return data
        return {"error": f"API error (HTTP {res.status_code})"}
    except Exception as e:
        return {"error": str(e)}

def format_pnr_message(pnr: str, data: dict) -> str:
    """Formats PNR data into a clean Telegram card."""
    if "error" in data:
        return f"❌ *Error checking PNR {pnr}:*\n`{data['error']}`"

    train_no = data.get("trainNumber", data.get("train_number", "N/A"))
    train_name = data.get("trainName", data.get("train_name", "Train"))
    doj = data.get("dateOfJourney", data.get("date_of_journey", "N/A"))
    source = data.get("sourceStation", data.get("source", data.get("from", "N/A")))
    dest = data.get("destinationStation", data.get("destination", data.get("to", "N/A")))
    chart = "✅ Chart Prepared" if data.get("chartPrepared", False) else "⏳ Chart Not Prepared"

    msg_lines = [
        f"🚆 *IRCTC PNR STATUS: {pnr}*",
        f"• *Train:* `{train_no}` - *{train_name}*",
        f"• *Date of Journey:* `{doj}`",
        f"• *Route:* `{source}` ➡️ `{dest}`",
        f"• *Charting:* {chart}\n",
        "*Passenger Details:*"
    ]

    passengers = data.get("passengerList", data.get("passengers", []))
    if isinstance(passengers, list) and passengers:
        for idx, p in enumerate(passengers, start=1):
            bk = p.get("bookingStatusDetails", p.get("booking_status", "N/A"))
            curr = p.get("currentStatusDetails", p.get("current_status", "N/A"))
            coach = p.get("coachPosition", p.get("coach", ""))
            berth = p.get("berthNumber", p.get("berth", ""))
            seat = f" ({coach}/{berth})" if coach and berth else ""
            msg_lines.append(f"  • *P{idx}:* Booked: `{bk}` ➡️ Current: *`{curr}`*{seat}")
    else:
        raw_status = data.get("currentStatus", data.get("bookingStatus", "Status details unavailable"))
        msg_lines.append(f"  • *Status:* `{raw_status}`")

    return "\n".join(msg_lines)

def check_tracked_pnrs():
    """Iterates through tracked PNRs and alerts on status changes."""
    for pnr, last_summary in list(tracked_pnrs.items()):
        new_data = get_pnr_status(pnr)
        if "error" not in new_data:
            new_summary = str(new_data.get("passengerList", new_data))
            if new_summary != last_summary:
                tracked_pnrs[pnr] = new_summary
                send_telegram(f"🔔 *PNR STATUS UPDATE DETECTED!*")
                send_telegram(format_pnr_message(pnr, new_data))

# =====================================================================
# MARKET QUOTE FETCHING
# =====================================================================
def get_quote(symbol: str):
    """Fetches real-time price & change% using Yahoo Finance API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        meta = data["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice", 0.0)
        prev_close = meta.get("chartPreviousClose", meta.get("previousClose", price))
        pct_change = ((price - prev_close) / prev_close) * 100 if prev_close else 0.0
        return price, pct_change
    except Exception:
        return 0.0, 0.0

def build_market_summary() -> str:
    """Builds a formatted snapshot of equity, crude, and US market indices."""
    symbols = {
        "Nifty 50": "^NSEI",
        "Bank Nifty": "^NSEBANK",
        "Crude Oil (WTI)": "CL=F",
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC"
    }
    
    ist_time = get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST")
    lines = [f"📊 *MARKET OVERVIEW BRIEFING*\n📅 `{ist_time}`\n"]

    for name, sym in symbols.items():
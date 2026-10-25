import time
import subprocess
import platform
from datetime import datetime
import requests

# ----------------- TELEGRAM CREDENTIALS -----------------
TELEGRAM_BOT_TOKEN = "8847366387:AAFFnPjhzAwJSN-pzdi0PvxGrL0xYVQZGug"
TELEGRAM_CHAT_ID = "5432795318"
# --------------------------------------------------------

PING_TARGETS = ["8.8.8.8", "1.1.1.1"]  # Google & Cloudflare DNS
CHECK_INTERVAL_SECONDS = 10           # Checks your Wi-Fi every 10 seconds

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=8)
    except Exception:
        pass

def ping_host(host: str):
    """Sends 1 quick ping to check if the internet responds."""
    param = "-n" if platform.system().lower() == "windows" else "-c"
    timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
    cmd = ["ping", param, "1", timeout_param, "1000", host]
    
    try:
        start = time.time()
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        round_trip = (time.time() - start) * 1000

        if res.returncode == 0:
            return True, round(round_trip, 1)
        return False, 0.0
    except Exception:
        return False, 0.0

def monitor():
    print("=" * 55)
    print("🛰️ Home Broadband Sentinel is Running...")
    print("Press Ctrl + C in this window to stop it anytime.")
    print("=" * 55)
    
    is_down = False
    down_start_time = None

    while True:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Ping the internet
        online_1, lat_1 = ping_host(PING_TARGETS[0])
        online_2, lat_2 = ping_host(PING_TARGETS[1])
        
        is_online = online_1 or online_2
        latency = max(lat_1, lat_2)

        if is_online:
            if is_down:
                # Connection was down, and just came back!
                down_end_time = datetime.now()
                total_down = str(down_end_time - down_start_time).split(".")[0]
                
                msg = (
                    f"🟢 *HOME BROADBAND RESTORED*\n\n"
                    f"• *Downtime Duration:* `{total_down}`\n"
                    f"• *Outage Started:* `{down_start_time.strftime('%H:%M:%S')}`\n"
                    f"• *Restored At:* `{down_end_time.strftime('%H:%M:%S')}`\n"
                    f"• *Current Latency:* `{latency} ms`"
                )
                print(f"[{now_str}] Broadband is back online! Sending Telegram alert...")
                send_telegram(msg)
                
                # Reset status
                is_down = False
                down_start_time = None
            else:
                print(f"[{now_str}] Internet OK | Ping: {latency} ms")
        else:
            if not is_down:
                is_down = True
                down_start_time = datetime.now()
                print(f"[{now_str}] 🔴 Outage detected! Internet is not responding...")

        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    monitor()
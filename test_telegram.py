import requests

TOKEN = "8847366387:AAFFnPjhzAwJSN-pzdi0PvxGrL0xYVQZGug"
CHAT_ID = "5432795318"

message = "🔔 *Market Bot Connected!*\n\nYour automated commodity alerts are now linked to this chat."
url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

response = requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
print(response.json())
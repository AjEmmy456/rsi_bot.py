from websocket import WebSocketApp  # Correct module: websocket-client
import json
import pandas as pd
import requests
from datetime import datetime

# Deriv API token
DERIV_API_TOKEN = "nivnGY70BJZClQw"
# Telegram bot credentials
BOT_TOKEN = "7754621698:AAGCmIfZ4ySst0QyMIJUZFseL4jf1aCYy5M"
CHAT_ID = "6555350340"

# Parameters
RSI_PERIOD = 14
candles = []

print("Starting script...")

# Function to send Telegram alerts
def send_telegram_alert(message):
    print("Attempting to send Telegram alert...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Alert sent successfully!")
    else:
        print(f"Failed to send alert: {response.text}")

# Function to calculate RSI
def calculate_rsi(data, period=14):
    print("Calculating RSI...")
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# WebSocket callback functions
def on_message(ws, message):
    global candles
    data = json.loads(message)

    if "tick" in data:
        tick = data["tick"]
        price = tick["quote"]
        timestamp = datetime.utcfromtimestamp(tick["epoch"])

        # Aggregate into 5-minute candles
        if not candles or (timestamp - candles[-1]["time"]).total_seconds() >= 300:
            candles.append({"time": timestamp, "Close": price})
        else:
            candles[-1]["Close"] = price

        print(f"Time: {timestamp}, Price: {price}")

        # Calculate RSI when enough 5-minute candles are available
        if len(candles) >= RSI_PERIOD:
            df = pd.DataFrame(candles)
            df["RSI"] = calculate_rsi(df, period=RSI_PERIOD)
            latest_rsi = df["RSI"].iloc[-1]
            print(f"Latest RSI: {latest_rsi}")

            # Send alert if RSI is below 40
            if latest_rsi < 40:
                print("RSI is below 40. Sending alert...")
                send_telegram_alert(f"RSI Alert: Current RSI is {latest_rsi:.2f}, which is below 40!")
                ws.close()  # Stop WebSocket after sending alert

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed")

def on_open(ws):
    print("WebSocket connection opened. Sending authorization message...")
    auth_message = {"authorize": DERIV_API_TOKEN}
    ws.send(json.dumps(auth_message))

    # Subscribe to R_50 ticks
    subscribe_message = {
        "ticks": "R_50",
        "subscribe": 1
    }
    ws.send(json.dumps(subscribe_message))
    print("Subscription message sent.")

# Connect to Deriv WebSocket
ws_url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
ws = WebSocketApp(
    ws_url,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

ws.on_open = on_open

# Run WebSocket
print("Running WebSocket...")
ws.run_forever()

            import streamlit as st
import yfinance as yf
import pandas as pd
import time
import requests

# --- TELEGRAM FUNCTION ---
def send_telegram_msg(message):
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
        requests.get(url)
    except Exception as e:
        st.error(f"Telegram Error: {e}")

st.set_page_config(page_title="Zerodha Live Tracker", layout="wide")
st.title("🏹 Zerodha Portfolio Sentinel")

# --- NEW: TELEGRAM TEST BUTTON ---
with st.sidebar:
    st.header("🔧 System Check")
    if st.button("🛠️ Test Telegram Connection"):
        try:
            token = st.secrets["TELEGRAM_TOKEN"]
            chat_id = st.secrets["TELEGRAM_CHAT_ID"]
            test_url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text=✅ App connected successfully to your Portfolio!"
            
            response = requests.get(test_url)
            if response.status_code == 200:
                st.success("Test message sent! Check Telegram.")
            else:
                st.error(f"Error {response.status_code}: {response.text}")
        except Exception as e:
            st.error(f"Secrets Error: {e}")

    st.divider()
    st.header("Alert Settings")
    loss_limit = st.number_input("Loss Threshold %", value=15.0)
    profit_limit = st.number_input("Profit Threshold %", value=115.0)

# --- FILE UPLOAD LOGIC ---
uploaded_file = st.file_uploader("Upload Zerodha P&L (Equity.csv)", type=['csv', 'xlsx'])

if uploaded_file:
    # 1. READ FILE (Handling Zerodha's top empty rows)
    if uploaded_file.name.endswith('.csv'):
        df_raw = pd.read_csv(uploaded_file, header=None)
    else:
        df_raw = pd.read_excel(uploaded_file, header=None)

    # Find the header row (where 'Symbol' exists)
    header_row_index = 0
    for i, row in df_raw.iterrows():
        if "Symbol" in row.values:
            header_row_index = i
            break
    
    # Re-read with correct header
    uploaded_file.seek(0)
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file, skiprows=header_row_index)
    else:
        df = pd.read_excel(uploaded_file, skiprows=header_row_index)

    # Filter out empty rows or total rows
    df = df[df['Symbol'].notna()]
    df = df[df['Symbol'] != 'Symbol'] 

    st.write(f"✅ Found {len(df)} stocks in your Zerodha file.")

    if st.button("🚀 START LIVE MONITORING"):
        st.session_state.monitoring = True
        st.session_state.portfolio_data = df

# --- MONITORING ENGINE ---
if st.session_state.get('monitoring'):
    monitor_area = st.empty()
    if 'sent_alerts' not in st.session_state:
        st.session_state.sent_alerts = set()

    while True:
        results = []
        for _, row in st.session_state.portfolio_data.iterrows():
            raw_ticker = str(row['Symbol']).strip().upper()
            ticker = f"{raw_ticker}.NS" # Add NSE suffix for Yahoo Finance
            
            try:
                # Zerodha Buy Price Logic:
                # Typically 'Buy Value' / 'Open Quantity'
                buy_val = float(row['Buy Value'])
                qty = float(row['Open Quantity'])
                buy_price = buy_val / qty if qty > 0 else 0
                
                # Get Live Price
                stock = yf.Ticker(ticker)
                # Using history for better reliability
                current_price = stock.history(period='1d')['Close'].iloc[-1]
                
                change = ((current_price - buy_price) / buy_price) * 100

                # Check Alerts
                if (change <= -loss_limit or change >= profit_limit) and raw_ticker not in st.session_state.sent_alerts:
                    alert_msg = f"🔔 *STOCK ALERT* 🔔\n\n*Stock:* {raw_ticker}\n*Move:* {change:.2f}%\n*Price:* ₹{current_price:.2f}"
                    send_telegram_msg(alert_msg)
                    st.session_state.sent_alerts.add(raw_ticker)

                results.append({
                    "Stock": raw_ticker,
                    "Avg Buy": round(buy_price, 2),
                    "Live Price": round(current_price, 2),
                    "Gain/Loss %": f"{change:.2f}%"
                })
            except:
                continue

        with monitor_area.container():
            st.table(pd.DataFrame(results))
            st.caption(f"Refreshing every 60s... Last update: {time.strftime('%H:%M:%S')}")
        
        time.sleep(60)
        st.rerun()

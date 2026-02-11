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

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔧 System Check")
    if st.button("🛠️ Test Telegram Connection"):
        token = st.secrets["TELEGRAM_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        test_url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text=✅ Connection Successful!"
        res = requests.get(test_url)
        if res.status_code == 200: st.success("Message sent!")
        else: st.error("Check Token/ID")

    st.divider()
    st.header("Alert Settings")
    loss_limit = st.number_input("Loss Threshold %", value=15.0)
    profit_limit = st.number_input("Profit Threshold %", value=115.0)

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Zerodha P&L (Equity.csv)", type=['csv', 'xlsx'])

# Safety Gate: Only run if a file exists
if uploaded_file:
    if 'portfolio_data' not in st.session_state:
        # Detect Zerodha header row
        df_raw = pd.read_csv(uploaded_file, header=None) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, header=None)
        
        header_row = 0
        for i, row in df_raw.iterrows():
            if "Symbol" in row.values:
                header_row = i
                break
        
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, skiprows=header_row) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, skiprows=header_row)
        
        # Clean Data
        df = df[df['Symbol'].notna()]
        df = df[df['Open Quantity'] > 0] # Only track what you currently hold
        st.session_state.portfolio_data = df

    st.write(f"✅ Ready to track {len(st.session_state.portfolio_data)} stocks.")
    
    if st.button("🚀 START MONITORING"):
        st.session_state.monitoring = True

# --- MONITORING ENGINE (Only runs if button was clicked) ---
if st.session_state.get('monitoring') and 'portfolio_data' in st.session_state:
    monitor_area = st.empty()
    if 'sent_alerts' not in st.session_state:
        st.session_state.sent_alerts = set()

    while True:
        results = []
        for _, row in st.session_state.portfolio_data.iterrows():
            raw_ticker = str(row['Symbol']).strip().upper()
            if raw_ticker == "SYMBOL": continue
            
            ticker = f"{raw_ticker}.NS"
            
            try:
                # Zerodha Column Math
                total_invested = float(row['Open Value'])
                qty = float(row['Open Quantity'])
                buy_price = total_invested / qty
                
                # Fetch Price
                stock = yf.Ticker(ticker)
                curr_price = stock.history(period='1d')['Close'].iloc[-1]
                change = ((curr_price - buy_price) / buy_price) * 100

                # Alerts
                if (change <= -loss_limit or change >= profit_limit) and raw_ticker not in st.session_state.sent_alerts:
                    send_telegram_msg(f"🔔 *STOCK ALERT*\n{raw_ticker}: {change:.2f}% (₹{curr_price:.2f})")
                    st.session_state.sent_alerts.add(raw_ticker)

                results.append({"Stock": raw_ticker, "Buy": round(buy_price, 2), "Live": round(curr_price, 2), "Change": f"{change:.2f}%"})
            except:
                continue

        with monitor_area.container():
            st.table(pd.DataFrame(results))
            st.caption(f"Last update: {time.strftime('%H:%M:%S')}")
        
        time.sleep(60)
        st.rerun()
else:
    if not uploaded_file:
        st.info("👋 Welcome! Please upload your Zerodha Equity CSV to begin.")
                

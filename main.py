import streamlit as st
import yfinance as yf
import pandas as pd
import time
import requests

# --- TELEGRAM FUNCTION ---
def send_telegram_msg(message):
    token = st.secrets["TELEGRAM_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
    try:
        requests.get(url)
    except Exception as e:
        st.error(f"Telegram failed: {e}")

# --- APP UI ---
st.set_page_config(page_title="Global Portfolio Monitor", page_icon="📈")
st.title("📈 Global Portfolio Monitor")
if st.button("🛠️ Test Telegram Connection"):
    token = st.secrets["TELEGRAM_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    test_url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text=App connected successfully!"
    
    response = requests.get(test_url)
    if response.status_code == 200:
        st.success("Test message sent! Check Telegram.")
    else:
        st.error(f"Error {response.status_code}: {response.text}")
st.write("Upload your Excel, set your targets, and get Telegram alerts.")

# Sidebar for Settings
st.sidebar.header("Alert Settings")
loss_limit = st.sidebar.number_input("Loss Alert %", value=15.0)
profit_limit = st.sidebar.number_input("Profit Alert %", value=115.0)

uploaded_file = st.file_uploader("Upload Broker Excel", type=['xlsx'])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    # Smart Detection
    t_cols = [c for c in df.columns if any(k in c.lower() for k in ['symbol', 'ticker', 'stock'])]
    p_cols = [c for c in df.columns if any(k in c.lower() for k in ['avg', 'buy', 'cost', 'price'])]

    col1, col2 = st.columns(2)
    t_col = col1.selectbox("Ticker Column", df.columns, index=df.columns.get_loc(t_cols[0]) if t_cols else 0)
    p_col = col2.selectbox("Buy Price Column", df.columns, index=df.columns.get_loc(p_cols[0]) if p_cols else 0)

    if st.button("Start Real-Time Tracking"):
        st.session_state.running = True
        st.session_state.data = df[[t_col, p_col]].dropna()

if st.session_state.get('running'):
    status_box = st.empty()
    sent_alerts = set()

    while True:
        display_list = []
        for _, row in st.session_state.data.iterrows():
            ticker = str(row[t_col]).strip().upper().split('.')[0]
            buy_price = float(row[p_col])
            
            try:
                # Get live data
                price = yf.Ticker(ticker).fast_info['last_price']
                change = ((price - buy_price) / buy_price) * 100
                
                # Logic for Telegram
                if (change <= -loss_limit or change >= profit_limit) and ticker not in sent_alerts:
                    msg = f"🔔 *STOCK ALERT* 🔔\n\n*Ticker:* {ticker}\n*Change:* {change:.2f}%\n*Current Price:* ${price:.2f}"
                    send_telegram_msg(msg)
                    sent_alerts.add(ticker)
                
                display_list.append({
                    "Stock": ticker, "Buy": f"${buy_price:.2f}", 
                    "Live": f"${price:.2f}", "Change %": f"{change:.2f}%"
                })
            except:
                continue

        with status_box.container():
            st.dataframe(pd.DataFrame(display_list), use_container_width=True)
            st.caption(f"Syncing... Last updated: {time.strftime('%H:%M:%S')}")
        
        time.sleep(60) # Wait 1 minute
        st.rerun()

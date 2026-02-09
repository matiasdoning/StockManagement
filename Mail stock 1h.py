import os
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import requests
from io import StringIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
import certifi

# --- SSL fix for macOS ---
ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl._create_default_https_context = lambda: ssl_context

# 1️⃣ TICKERS
def get_custom_tickers():
    return ["ASML.AS", "MC.PA", "SAP.DE", "LIN.DE", "TTE.PA", "SIE.DE", "AI.PA", "SAN.PA", "ALV.DE", "SU.PA", "OR.PA", "ISP.MI", "COL.MC", "AIR.PA", "KER.PA", "DG.PA", "DTE.DE", "BAS.DE", "BNP.PA", "DTG.DE", "ABI.BR", "INGA.AS", "SAF.PA", "ENEL.MI", "DB1.DE", "EL.PA", "UCG.MI", "PRX.AS", "CS.PA", "MUV2.DE", "RACE.MI", "BMW.DE", "SAN.MC", "STLAM.MI", "IFX.DE", "IBE.MC", "ADYEN.AS", "VNA.DE", "MBG.DE", "DHL.DE", "ENR.DE", "RI.PA", "ENI.MI", "ITX.MC", "ASRNL.AS", "PHG", "CRH", "ADS.DE", "NVDA", "AAPL", "MSFT", "AMZN", "META", "AVGO", "GOOGL", "GOOG", "TSLA", "BRK-B", "WMT", "JPM", "ORCL", "LLY", "V", "MA", "XOM", "NFLX", "JNJ", "PLTR", "COST", "AMD", "ABBV", "BAC", "HD", "PG", "UNH", "GE", "CVX", "KO", "IBM", "CSCO", "WFC", "MS", "AXP", "MU", "PM", "CAT", "TMUS", "CRM", "GS", "RTX", "ABT", "MRK", "MCD", "TMO", "APP", "LIN", "PEP", "DIS", "UBER", "ISRG", "ANET", "NOW", "LRCX", "INTU", "QCOM", "AMAT", "INTC", "T", "C", "BLK", "NEE", "SCHW", "BA", "BKNG", "VZ", "APH", "GEV", "TJX", "DHR", "AMGN", "KLAC", "TXN", "ACN", "GILD", "BSX", "SPGI", "ADBE", "PANW", "ETN", "SYK", "COF", "PFE", "HON", "LOW", "CRWD", "UNP", "PGR", "DE", "HOOD", "CEG", "BX", "MDT", "WELL", "PLD", "ADI", "ADP", "LMT", "CB"]  # tu lista completa

# 2️⃣ RSI y Bollinger Bands intradía
def compute_rsi_fast(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_bollinger_bands_fast(series, window=20):
    sma = series.rolling(window=window, min_periods=window).mean()
    std = series.rolling(window=window, min_periods=window).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    bb_pos = (series - lower) / (upper - lower)
    return sma, upper, lower, bb_pos

# 3️⃣ Posiciones abiertas (ejemplo desde Google Sheets)
def read_google_sheet(sheet_url):
    try:
        if '/edit?' in sheet_url:
            csv_url = sheet_url.replace('/edit?', '/export?')
        else:
            csv_url = sheet_url + '/export?format=csv'
        response = requests.get(csv_url)
        df = pd.read_csv(StringIO(response.text))
        return df
    except:
        return pd.DataFrame()

def get_open_positions():
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1K9QCGPgBiAJM7G4a_D7cmUmxMckQKKdIv-7STRFURrU"
    df = read_google_sheet(SHEET_URL)
    if df.empty:
        return []
    open_positions = df[df['Estado'] == 'ABIERTA']
    return open_positions.to_dict('records')

# 4️⃣ Analizar tickers intradía
def analyze_tickers(tickers):
    results = []
    for ticker in tickers:
        try:
            data = yf.download(
                ticker, period="3d", interval="1h", progress=False, auto_adjust=True
            )
            if data.empty:
                continue
            close = data["Close"].squeeze()
            rsi = compute_rsi_fast(close, period=14)
            sma, upper, lower, bb_pos = compute_bollinger_bands_fast(close, window=20)
            latest_close = close.iloc[-1]
            latest_rsi = rsi.iloc[-1]
            latest_bb_pos = bb_pos.iloc[-1]
            results.append({
                "Ticker": ticker,
                "Price": round(latest_close,2),
                "RSI": round(latest_rsi,2),
                "BB_Position": round(latest_bb_pos,3),
                "Date": data.index[-1].strftime("%Y-%m-%d %H:%M")
            })
        except:
            continue
    return pd.DataFrame(results).dropna()

# 5️⃣ Generar señales
def generate_signals(df, open_positions):
    owned_tickers = [pos['Ticker'] for pos in open_positions]
    df_buy = df[(df["RSI"] <= 20) & (df["BB_Position"] < 0)]
    df_buy = df_buy[~df_buy['Ticker'].isin(owned_tickers)].sort_values("RSI")
    df_sell = df[(df["RSI"] >= 80) & (df["BB_Position"] > 1)]
    df_sell = df_sell[df_sell['Ticker'].isin(owned_tickers)].sort_values("RSI", ascending=False)
    return df_buy, df_sell

# 6️⃣ Enviar email
def send_email(df_buy, df_sell, open_positions):
    sender_email = os.environ.get("EMAIL_USER")
    sender_password = os.environ.get("rgzh scts sxhn ilkp")
    recipient_email = os.environ.get("EMAIL_USER")

    subject = f"📊 Trading Hourly Alert - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    body = f"<h2>📈 Señales de Trading - {datetime.now().strftime('%d/%m/%Y %H:%M')}</h2>"

    # Portafolio
    body += f"<h3>💰 Portafolio Actual ({len(open_positions)})</h3>"
    if open_positions:
        portfolio_html = "<table border='1'><tr><th>Ticker</th><th>Acción</th><th>Precio</th><th>Shares</th><th>Fecha</th></tr>"
        for pos in open_positions:
            portfolio_html += f"<tr><td>{pos['Ticker']}</td><td>{pos['Accion']}</td><td>${pos['Precio']}</td><td>{pos['Shares']}</td><td>{pos['Fecha']}</td></tr>"
        portfolio_html += "</table>"
        body += portfolio_html
    else:
        body += "<p>No hay posiciones abiertas.</p>"

    # Compra
    body += "<h3>🟢 SEÑALES DE COMPRA</h3>"
    if not df_buy.empty:
        buy_html = "<table border='1'><tr><th>Ticker</th><th>Precio</th><th>RSI</th><th>BB Pos</th></tr>"
        for _, s in df_buy.iterrows():
            buy_html += f"<tr><td>{s['Ticker']}</td><td>${s['Price']}</td><td>{s['RSI']}</td><td>{s['BB_Position']}</td></tr>"
        buy_html += "</table>"
        body += buy_html
    else:
        body += "<p>No hay señales de compra.</p>"

    # Venta
    body += "<h3>🔴 SEÑALES DE VENTA</h3>"
    if not df_sell.empty:
        sell_html = "<table border='1'><tr><th>Ticker</th><th>Precio</th><th>RSI</th><th>BB Pos</th><th>Acción</th></tr>"
        for _, s in df_sell.iterrows():
            sell_html += f"<tr><td>{s['Ticker']}</td><td>${s['Price']}</td><td>{s['RSI']}</td><td>{s['BB_Position']}</td><td>VENDER</td></tr>"
        sell_html += "</table>"
        body += sell_html
    else:
        body += "<p>No hay señales de venta.</p>"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.attach(MIMEText(body, "html"))

    try:
        context = ssl.create_default_context(cafile=certifi.where())
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"📨 Email enviado a {recipient_email}")
    except Exception as e:
        print(f"Error enviando email: {e}")

# 7️⃣ MAIN
def main():
    tickers = get_custom_tickers()
    open_positions = get_open_positions()
    df = analyze_tickers(tickers)
    df_buy, df_sell = generate_signals(df, open_positions)
    print(f"📊 Signals found - Buy: {len(df_buy)}, Sell: {len(df_sell)}")
    
    # Only send email if there is at least one trade signal
    if not df_buy.empty or not df_sell.empty:
        send_email(df_buy, df_sell, open_positions)
        print("✅ Email sent with trade signals")
    else:
        send_email(df_buy, df_sell, open_positions)
        print("ℹ️ No trade signals - no email sent")

if __name__ == "__main__":
    main()

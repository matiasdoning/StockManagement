"""
Daily Custom Tickers RSI & Bollinger Analysis
Author: Matias
Goal: Identify potential BUY/SELL opportunities daily around 14h
"""

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
import random

# --- SSL fix for macOS ---
ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl._create_default_https_context = lambda: ssl_context

# =====================================================
# 1. CUSTOM TICKERS LIST - MODIFY THIS SECTION
# =====================================================
def get_custom_tickers():
    """
    Replace this list with your desired tickers
    Add any stocks, ETFs, or other securities you want to monitor
    """
    CUSTOM_TICKERS = [
        "ASML.AS", "MC.PA", "SAP.DE", "LIN.DE", "TTE.PA", "SIE.DE", "AI.PA", "SAN.PA", "ALV.DE", "SU.PA", "OR.PA", "ISP.MI", "COL.MC", "AIR.PA", "KER.PA", "DG.PA", "DTE.DE", "BAS.DE", "BNP.PA", "DTG.DE", "ABI.BR", "INGA.AS", "SAF.PA", "ENEL.MI", "DB1.DE", "EL.PA", "UCG.MI", "PRX.AS", "CS.PA", "MUV2.DE", "RACE.MI", "BMW.DE", "SAN.MC", "STLAM.MI", "IFX.DE", "IBE.MC", "ADYEN.AS", "VNA.DE", "MBG.DE", "DHL.DE", "ENR.DE", "RI.PA", "ENI.MI", "ITX.MC", "ASRNL.AS", "PHG.AS", "CRH", "ADS.DE", "NVDA", "AAPL", "MSFT", "AMZN", "META", "AVGO", "GOOGL", "GOOG", "TSLA", "BRK.B", "WMT", "JPM", "ORCL", "LLY", "V", "MA", "XOM", "NFLX", "JNJ", "PLTR", "COST", "AMD", "ABBV", "BAC", "HD", "PG", "UNH", "GE", "CVX", "KO", "IBM", "CSCO", "WFC", "MS", "AXP", "MU", "PM", "CAT", "TMUS", "CRM", "GS", "RTX", "ABT", "MRK", "MCD", "TMO", "APP", "LIN", "PEP", "DIS", "UBER", "ISRG", "ANET", "NOW", "LRCX", "INTU", "QCOM", "AMAT", "INTC", "T", "C", "BLK", "NEE", "SCHW", "BA", "BKNG", "VZ", "APH", "GEV", "TJX", "DHR", "AMGN", "KLAC", "TXN", "ACN", "GILD", "BSX", "SPGI", "ADBE", "PANW", "ETN", "SYK", "COF", "PFE", "HON", "LOW", "CRWD", "UNP", "PGR", "DE", "HOOD", "CEG", "BX", "MDT", "WELL", "PLD", "ADI", "ADP", "LMT", "CB"
    ]
    return CUSTOM_TICKERS

# =====================================================
# 2. Compute RSI (14) - Wilder's Method
# =====================================================
def compute_rsi(series, period=14):
    delta = series.diff()

    # Separate gains and losses
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Initialize average gains and losses using the first 'period' values
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Use Wilder's smoothing for subsequent values
    for i in range(period, len(series)):
        if i == period:
            continue
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi

# =====================================================
# 3. Compute Bollinger Bands (20)
# =====================================================
def compute_bollinger_bands(series, window=20):
    sma = series.rolling(window).mean()
    std = series.rolling(window).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    return sma, upper, lower

# =====================================================
# 4. Calculate Indicators for All Stocks
# =====================================================
def analyze_tickers(tickers):
    results = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    for ticker in tickers:
        try:
            data = yf.download(
                ticker, start=start_str, end=end_str, progress=False, threads=True, auto_adjust=True
            )

            if data.empty:
                print(f"⚠️ {ticker}: No data")
                continue

            # Handle MultiIndex safely
            if isinstance(data.columns, pd.MultiIndex):
                if "Close" in data.columns.get_level_values(0):
                    close = data["Close"]
                    # If still has multiple levels, droplevel
                    if isinstance(close.columns, pd.MultiIndex):
                        close = close.droplevel(0, axis=1)
                    close = close.squeeze()  # Convert to Series if single column DataFrame
                else:
                    print(f"⚠️ {ticker}: 'Close' column not found in MultiIndex")
                    continue
            else:
                close = data["Close"]

            # Convert to Series just in case
            if isinstance(close, pd.DataFrame):
                close = close.squeeze()

            rsi = compute_rsi(close)
            sma, upper, lower = compute_bollinger_bands(close)

            latest_close = close.iloc[-1]
            latest_rsi = rsi.iloc[-1]
            latest_sma = sma.iloc[-1]
            latest_upper = upper.iloc[-1]
            latest_lower = lower.iloc[-1]

            position = (latest_close - latest_lower) / (latest_upper - latest_lower)

            results.append({
                "Ticker": ticker,
                "Price": round(latest_close, 2),
                "RSI": round(latest_rsi, 2),
                "BB_Position": round(position, 2),
                "Upper_BB": round(latest_upper, 2),
                "Lower_BB": round(latest_lower, 2),
                "SMA20": round(latest_sma, 2),
                "Date": data.index[-1].strftime("%Y-%m-%d")
            })

        except Exception as e:
            print(f"⚠️ Error with {ticker}: {e}")
            continue

    df = pd.DataFrame(results)
    return df.dropna()

# =====================================================
# 5. Generate Buy/Sell Signals
# =====================================================
def generate_signals(df):
    df_buy = df[(df["RSI"] < 30) & (df["BB_Position"] < 0.1)]
    df_sell = df[(df["RSI"] > 70) & (df["BB_Position"] > 0.9)]
    df_buy = df_buy.sort_values(by="RSI", ascending=True)
    df_sell = df_sell.sort_values(by="RSI", ascending=False)
    return df_buy, df_sell

# =====================================================
# 6. Generate Random Sample for Statistical Control
# =====================================================
def generate_random_sample(df, n=10):
    if len(df) <= n:
        return df
    random_tickers = random.sample(df["Ticker"].tolist(), n)
    df_random = df[df["Ticker"].isin(random_tickers)]
    return df_random

# =====================================================
# 7. Send Email 
# =====================================================
def send_email(df_buy, df_sell, df_random, recipient_email):
    sender_email = "matiasdoning@gmail.com"
    sender_password = "rgzh scts sxhn ilkp"  # App password for Gmail

    subject = f"Daily RSI/Bollinger Signals - {datetime.now().strftime('%Y-%m-%d')}"
    body = "<h2>📈 Custom Portfolio Daily Analysis</h2>"

    # --- Buy Section ---
    body += "<h3>🟢 Buy Opportunities (Oversold)</h3>"
    if not df_buy.empty:
        body += df_buy.to_html(index=False)
    else:
        body += "<p>No buy signals today.</p>"

    # --- Sell Section ---
    body += "<h3>🔴 Sell Opportunities (Overbought)</h3>"
    if not df_sell.empty:
        body += df_sell.to_html(index=False)
    else:
        body += "<p>No sell signals today.</p>"

    # --- Random Sample Section ---
    body += "<h3>🎲 Random Control Sample (10 Stocks)</h3>"
    body += df_random.to_html(index=False)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.attach(MIMEText(body, "html"))

    context = ssl.create_default_context(cafile=certifi.where())
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)
    print(f"📨 Email sent to {recipient_email}")

# =====================================================
# 8. Main Execution
# =====================================================
def main():
    print("Loading custom tickers...")
    tickers = get_custom_tickers()
    print(f"Total: {len(tickers)} custom tickers")
    print(f"Tickers: {tickers}")

    print("Downloading and analyzing data...")
    df = analyze_tickers(tickers)

    print("Generating signals...")
    df_buy, df_sell = generate_signals(df)

    print("Selecting random sample...")
    df_random = generate_random_sample(df)

    print("\n🟢 Buy candidates:")
    if not df_buy.empty:
        print(df_buy[["Ticker", "Price", "RSI", "BB_Position"]].head(10))
    else:
        print("No buy candidates today")

    print("\n🔴 Sell candidates:")
    if not df_sell.empty:
        print(df_sell[["Ticker", "Price", "RSI", "BB_Position"]].head(10))
    else:
        print("No sell candidates today")

    # Save locally
    df_buy.to_csv("/Users/matiasdoning/Downloads/custom_buy_signals.csv", index=False)
    df_sell.to_csv("/Users/matiasdoning/Downloads/custom_sell_signals.csv", index=False)
    df.to_csv("/Users/matiasdoning/Downloads/custom_full_analysis.csv", index=False)

    print(f"\n📊 Analysis saved to:")
    print(f"  - /Users/matiasdoning/Downloads/custom_buy_signals_1.csv")
    print(f"  - /Users/matiasdoning/Downloads/custom_sell_signals_1.csv")
    print(f"  - /Users/matiasdoning/Downloads/custom_full_analysis_1.csv")

    # Send email
    send_email(df_buy, df_sell, df_random, "matiasdoning@gmail.com")

if __name__ == "__main__":
    main()

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

# =====================================================
# 1. CONFIGURACIÓN
# =====================================================
def get_custom_tickers():
    """Tu lista de tickers personalizada"""
    CUSTOM_TICKERS = [
       "IBM", "PFE", "C", "GE", "INTC", "GS", "BAC", "VZ", "CSCO", "XOM", 
       "JPM", "AMGN", "AMD", "BKNG", "JNJ", "CAT", "CVX", "PG", "MDT", "DE", 
       "HON", "T", "PEP", "DIS", "SPGI", "LLY", "HD", "PM", "LOW", "COF", 
       "QCOM", "WFC", "PLD", "BA", "ABT", "BLK", "MU", "ADP", "WMT", "NEE", 
       "BX", "ORCL", "AXP", "UNH", "PGR", "ADBE", "MS", "MRK", "MCD", "KO", 
       "BSX", "ISRG", "RTX", "CB", "KLAC", "TXN", "TSLA", "GOOGL", "ADI", 
       "SYK", "ACN", "LIN", "SCHW", "GOOG", "AMZN", "TMUS", "UNP", "AAPL", 
       "DHR", "LMT", "ETN", "PANW", "MSFT", "AMAT", "COST", "TMO", "NVDA", 
       "WELL", "APH", "TJX", "LRCX", "NFLX", "ABBV", "GILD", "META", "CRM", 
       "INTU", "MA", "ANET", "AVGO", "V", "NOW", "CRWD", "UBER", "HOOD", 
       "APP", "CEG", "PLTR", "GEV"
    ]
    return CUSTOM_TICKERS

# =====================================================
# 2. INDICADORES EXACTAMENTE COMO EL BACKTEST
# =====================================================
def compute_rsi_fast(series, period=14):
    """✅ RSI EXACTO como en tu backtest (Yahoo Finance method)"""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Use exponential moving average for smoother calculation (Yahoo method)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_bollinger_bands_fast(series, window=20):
    """✅ Bollinger Bands EXACTO como en tu backtest"""
    sma = series.rolling(window=window, min_periods=window).mean()
    std = series.rolling(window=window, min_periods=window).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    bb_pos = (series - lower) / (upper - lower)
    return sma, upper, lower, bb_pos

# =====================================================
# 3. GOOGLE SHEETS PÚBLICO (SIN CREDENCIALES)
# =====================================================
def read_google_sheet(sheet_url):
    """
    Lee Google Sheets público sin credenciales
    """
    try:
        if '/edit?' in sheet_url:
            csv_url = sheet_url.replace('/edit?', '/export?')
        else:
            csv_url = sheet_url + '/export?format=csv'
        
        response = requests.get(csv_url)
        df = pd.read_csv(StringIO(response.text))
        return df
    except Exception as e:
        print(f"Error leyendo Google Sheet: {e}")
        return pd.DataFrame()

def get_open_positions():
    """Obtiene posiciones abiertas desde Google Sheets"""
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1K9QCGPgBiAJM7G4a_D7cmUmxMckQKKdIv-7STRFURrU"
    
    df = read_google_sheet(SHEET_URL)
    if df.empty:
        return []
    
    open_positions = df[df['Estado'] == 'ABIERTA']
    return open_positions.to_dict('records')

# =====================================================
# 4. ANÁLISIS TÉCNICO CON INDICADORES CORREGIDOS
# =====================================================
def analyze_tickers(tickers):
    """Analiza tickers con indicadores EXACTOS como el backtest"""
    results = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)

    for ticker in tickers:
        try:
            data = yf.download(
                ticker, start=start_date, end=end_date, progress=False, auto_adjust=True
            )

            if data.empty:
                continue

            # Manejar datos
            if isinstance(data.columns, pd.MultiIndex):
                if "Close" in data.columns.get_level_values(0):
                    close = data["Close"]
                    if isinstance(close.columns, pd.MultiIndex):
                        close = close.droplevel(0, axis=1)
                    close = close.squeeze()
                else:
                    continue
            else:
                close = data["Close"]

            if isinstance(close, pd.DataFrame):
                close = close.squeeze()

            # ✅ CALCULAR INDICADORES EXACTAMENTE COMO BACKTEST
            rsi = compute_rsi_fast(close, period=14)
            sma, upper, lower, bb_pos = compute_bollinger_bands_fast(close, window=20)

            latest_close = close.iloc[-1]
            latest_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
            latest_bb_pos = bb_pos.iloc[-1] if not pd.isna(bb_pos.iloc[-1]) else 0.5

            results.append({
                "Ticker": ticker,
                "Price": round(latest_close, 2),
                "RSI": round(latest_rsi, 2),
                "BB_Position": round(latest_bb_pos, 3),
                "Date": data.index[-1].strftime("%Y-%m-%d")
            })

        except Exception as e:
            continue

    return pd.DataFrame(results).dropna()

# =====================================================
# 5. GENERAR SEÑALES (RESTO DEL CÓDIGO IGUAL)
# =====================================================
def generate_signals(df, open_positions):
    """Genera señales considerando posiciones abiertas"""
    owned_tickers = [pos['Ticker'] for pos in open_positions]
    
    # Señales de COMPRA (solo para tickers que no tenemos)
    df_buy = df[(df["RSI"] < 30) & (df["BB_Position"] < 0.1)]
    df_buy = df_buy[~df_buy['Ticker'].isin(owned_tickers)]
    df_buy = df_buy.sort_values(by="RSI", ascending=True)
    
    # Señales de VENTA (solo para tickers que tenemos)
    df_sell = df[(df["RSI"] > 70) | (df["BB_Position"] > 0.9)]
    df_sell = df_sell[df_sell['Ticker'].isin(owned_tickers)]
    df_sell = df_sell.sort_values(by="RSI", ascending=False)
    
    return df_buy, df_sell

# =====================================================
# 6. EMAIL (IGUAL)
# =====================================================
def send_email(df_buy, df_sell, open_positions):
    sender_email = "matiasdoning@gmail.com"
    sender_password = "rgzh scts sxhn ilkp"
    recipient_email = "matiasdoning@gmail.com"

    subject = f"Señales Trading - {datetime.now().strftime('%d/%m/%Y')}"
    
    body = f"""
<h2>📈 Análisis Diario - {datetime.now().strftime('%d/%m/%Y %H:%M')}</h2>

<h3>💰 PORTAFOLIO ACTUAL ({len(open_positions)} posiciones)</h3>
"""
    
    if open_positions:
        portfolio_html = "<table border='1'><tr><th>Ticker</th><th>Acción</th><th>Precio</th><th>Shares</th><th>Fecha</th></tr>"
        for pos in open_positions:  
            portfolio_html += f"<tr><td>{pos['Ticker']}</td><td>{pos['Accion']}</td><td>${pos['Precio']}</td><td>{pos['Shares']}</td><td>{pos['Fecha']}</td></tr>"
        portfolio_html += "</table>"
        body += portfolio_html
    else:
        body += "<p>No hay posiciones abiertas.</p>"

    # Señales de COMPRA
    body += "<h3>🟢 SEÑALES DE COMPRA</h3>"
    if not df_buy.empty:
        buy_html = "<table border='1'><tr><th>Ticker</th><th>Precio</th><th>RSI</th><th>BB Pos</th><th>Shares Sugeridos</th></tr>"
        for _, signal in df_buy.iterrows():
            shares = int(500 / signal['Price'])
            buy_html += f"<tr><td>{signal['Ticker']}</td><td>${signal['Price']}</td><td>{signal['RSI']}</td><td>{signal['BB_Position']}</td><td>{shares}</td></tr>"
        buy_html += "</table>"
        body += buy_html
    else:
        body += "<p>No hay señales de compra hoy.</p>"

    # Señales de VENTA
    body += "<h3>🔴 SEÑALES DE VENTA</h3>"
    if not df_sell.empty:
        sell_html = "<table border='1'><tr><th>Ticker</th><th>Precio</th><th>RSI</th><th>BB Pos</th><th>Acción</th></tr>"
        for _, signal in df_sell.iterrows():
            sell_html += f"<tr><td>{signal['Ticker']}</td><td>${signal['Price']}</td><td>{signal['RSI']}</td><td>{signal['BB_Position']}</td><td>VENDER</td></tr>"
        sell_html += "</table>"
        body += sell_html
    else:
        body += "<p>No hay señales de venta hoy.</p>"

    # Enviar email
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

# =====================================================
# 7. EJECUCIÓN PRINCIPAL
# =====================================================
def main():
    print("🚀 INICIANDO ANÁLISIS DIARIO CON INDICADORES EXACTOS...")
    
    tickers = get_custom_tickers()
    print(f"📊 Analizando {len(tickers)} tickers")
    
    open_positions = get_open_positions()
    print(f"   Posiciones abiertas: {len(open_positions)}")
    
    df = analyze_tickers(tickers)
    
    df_buy, df_sell = generate_signals(df, open_positions)
    
    print(f"\n📊 RESULTADOS:")
    print(f"   Señales COMPRA: {len(df_buy)}")
    print(f"   Señales VENTA: {len(df_sell)}")
    
    if not df_buy.empty:
        print(f"\n🟢 COMPRAR:")
        for _, signal in df_buy.head(5).iterrows():
            shares = int(500 / signal['Price'])
            print(f"   {signal['Ticker']} - ${signal['Price']} (RSI: {signal['RSI']}, BB: {signal['BB_Position']})")
    
    if not df_sell.empty:
        print(f"\n🔴 VENDER:")
        for _, signal in df_sell.head(5).iterrows():
            print(f"   {signal['Ticker']} - ${signal['Price']} (RSI: {signal['RSI']}, BB: {signal['BB_Position']})")
    
    send_email(df_buy, df_sell, open_positions)
    print("✅ ANÁLISIS COMPLETADO CON INDICADORES EXACTOS")

if __name__ == "__main__":
    main()
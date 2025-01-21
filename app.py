import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime, timedelta, timezone
from coinbase.rest import RESTClient
import requests
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Inicializa cliente Coinbase
class CoinbaseClient:
    def __init__(self):
        self.base_url = "https://api.exchange.coinbase.com"
        api_key = os.getenv('COINBASE_API_KEY')
        api_secret = os.getenv('COINBASE_API_SECRET')
        
        if not api_key or not api_secret:
            raise ValueError("Credenciais da API não encontradas no arquivo .env")
        
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "Coinbase Bot",
        }
    
    def get_market_data(self, product_id, granularity, days_back=7):
        """Obtém dados históricos do mercado usando a API pública do Coinbase"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        
        url = f"{self.base_url}/products/{product_id}/candles"
        params = {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "granularity": granularity,
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            raise ValueError(f"Erro na API Coinbase: {response.json().get('message', 'Erro desconhecido')}")
        
        candles = response.json()
        df = pd.DataFrame(candles, columns=['time', 'low', 'high', 'open', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        df.set_index('time', inplace=True)
        return df

def calculate_ema_strategy(df, short_window=9, long_window=21):
    """Calcula EMAs e sinais de trading"""
    df['ema_short'] = df['close'].ewm(span=short_window, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long_window, adjust=False).mean()
    
    # Gera sinais
    df['signal'] = 0
    df.loc[df['ema_short'] > df['ema_long'], 'signal'] = 1  # Sinal de compra
    df.loc[df['ema_short'] < df['ema_long'], 'signal'] = -1 # Sinal de venda
    
    return df

def backtest_ema(df, initial_capital=1000.0):
    """Executa backtest da estratégia"""
    position = 0
    balance = initial_capital
    portfolio = []
    
    for idx, row in df.iterrows():
        if row['signal'] == 1 and position == 0:  # Compra
            position = balance / row['close']
            balance = 0
        elif row['signal'] == -1 and position > 0:  # Venda
            balance = position * row['close']
            position = 0
            
        # Calcula valor atual do portfólio
        portfolio_value = balance + (position * row['close'] if position > 0 else 0)
        portfolio.append(portfolio_value)
    
    df['portfolio_value'] = portfolio
    roi = ((portfolio[-1] - initial_capital) / initial_capital) * 100
    
    return df, roi

# ===================================
# CONFIGURAÇÕES STREAMLIT
# ===================================
st.set_page_config(page_title="Bot Trader Coinbase", layout="wide")

st.title("Bot Trader Coinbase - Estratégia EMA")

# Sidebar - Parâmetros
st.sidebar.header("Parâmetros de Estratégia")
product_id = st.sidebar.text_input("Par de Mercado (ex: BTC-USD)", value="BTC-USD")

# Dicionário de conversão de intervalos
GRANULARITY_MAP = {
    "1 minuto": 60,
    "5 minutos": 300,
    "15 minutos": 900,
    "30 minutos": 1800,
    "1 hora": 3600,
    "6 horas": 21600,
    "1 dia": 86400
}

interval = st.sidebar.selectbox(
    "Intervalo de Candle", 
    list(GRANULARITY_MAP.keys()),
    index=2
)

short_window = st.sidebar.number_input("Short EMA Window", min_value=1, value=9)
long_window = st.sidebar.number_input("Long EMA Window", min_value=1, value=21)
days_back = st.sidebar.number_input("Dias de histórico", min_value=1, value=7)

# Valor inicial
initial_capital = st.number_input("Valor inicial de aplicação (USD):", min_value=10.0, value=1000.0)

# Botão para carregar dados e executar
if st.button("Carregar Dados e Backtest"):
    try:
        # Inicializa cliente
        client = CoinbaseClient()
        
        # Carrega dados
        df = client.get_market_data(
            product_id=product_id,
            granularity=GRANULARITY_MAP[interval],
            days_back=days_back
        )
        
        if df.empty:
            st.error("Não foi possível obter dados do mercado. Verifique se o par está correto.")
        else:
            # Calcula estratégia
            df = calculate_ema_strategy(df, short_window=short_window, long_window=long_window)
            
            # Executa backtest
            df_backtest, roi_final = backtest_ema(df, initial_capital=initial_capital)
            
            st.write(f"ROI final: **{roi_final:.2f}%**")

            # Plot Candlestick
            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="Candles"
            ))

            # EMAs
            fig.add_trace(go.Scatter(
                x=df.index, 
                y=df["ema_short"], 
                line=dict(color='blue', width=1), 
                name=f"EMA {short_window}"
            ))

            fig.add_trace(go.Scatter(
                x=df.index, 
                y=df["ema_long"], 
                line=dict(color='red', width=1), 
                name=f"EMA {long_window}"
            ))

            # Sinais
            buy_signals = df[df["signal"] == 1]
            sell_signals = df[df["signal"] == -1]

            fig.add_trace(go.Scatter(
                x=buy_signals.index,
                y=buy_signals["close"],
                mode="markers",
                marker_symbol="triangle-up",
                marker_color="green",
                marker_size=10,
                name="Compra"
            ))

            fig.add_trace(go.Scatter(
                x=sell_signals.index,
                y=sell_signals["close"],
                mode="markers",
                marker_symbol="triangle-down",
                marker_color="red",
                marker_size=10,
                name="Venda"
            ))

            fig.update_layout(
                title=f"{product_id} - Intervalo {interval}",
                xaxis_title="Tempo",
                yaxis_title="Preço",
                xaxis_rangeslider_visible=False,
                height=700
            )

            st.plotly_chart(fig, use_container_width=True)

            # Plot portfolio
            fig_portfolio = go.Figure()
            fig_portfolio.add_trace(go.Scatter(
                x=df_backtest.index,
                y=df_backtest["portfolio_value"],
                line=dict(color='purple', width=2),
                name="Evolução do Portfólio"
            ))
            
            fig_portfolio.update_layout(
                title="Evolução do Portfólio ao longo do tempo",
                xaxis_title="Tempo",
                yaxis_title="Valor USD",
                height=400
            )

            st.plotly_chart(fig_portfolio, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")

# Seção de Trading Real
st.header("Operação em Conta Real")
st.warning("""
⚠️ **Atenção:** Trading em criptomoedas envolve riscos significativos. 
Use por sua conta e risco e nunca invista mais do que pode perder.
""")

if st.button("EXECUTAR TRADE REAL"):
    try:
        client = CoinbaseClient()
        
        # Obtém dados mais recentes
        df = client.get_market_data(
            product_id=product_id,
            granularity=GRANULARITY_MAP[interval],
            days_back=1
        )
        
        # Calcula sinais
        df = calculate_ema_strategy(df, short_window=short_window, long_window=long_window)
        current_signal = df['signal'].iloc[-1]
        current_price = df['close'].iloc[-1]
        
        if current_signal == 1:
            st.info(f"Sinal de COMPRA detectado em {current_price:.2f}")
            # Aqui você implementaria a lógica de compra real
        elif current_signal == -1:
            st.info(f"Sinal de VENDA detectado em {current_price:.2f}")
            # Aqui você implementaria a lógica de venda real
        else:
            st.info("Nenhum sinal de trading detectado no momento")
            
    except Exception as e:
        st.error(f"Erro ao executar trade: {str(e)}")
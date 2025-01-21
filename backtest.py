import pandas as pd
import numpy as np

def prepare_data(kline_data):
    """
    Converte a lista de klines em um DataFrame do pandas com colunas:
    [timestamp, open, high, low, close, volume]
    Formato original da CoinEx: [timestamp, open, close, high, low, volume]
    """
    df = pd.DataFrame(kline_data, columns=["timestamp", "open", "close", "high", "low", "volume"])
    # Converte para tipos numéricos
    df["open"] = pd.to_numeric(df["open"], errors='coerce')
    df["high"] = pd.to_numeric(df["high"], errors='coerce')
    df["low"] = pd.to_numeric(df["low"], errors='coerce')
    df["close"] = pd.to_numeric(df["close"], errors='coerce')
    df["volume"] = pd.to_numeric(df["volume"], errors='coerce')
    # Timestamp em segundos -> converte para datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s')
    df.set_index("timestamp", inplace=True)
    df.sort_index(inplace=True)
    return df

def calculate_ema_strategy(df, short_window=9, long_window=21):
    """
    Calcula as EMAs e retorna DataFrame com colunas:
    - 'ema_short'
    - 'ema_long'
    - 'signal' => (1 para Compra, -1 para Venda, 0 para Neutro)
    """
    df["ema_short"] = df["close"].ewm(span=short_window, adjust=False).mean()
    df["ema_long"]  = df["close"].ewm(span=long_window, adjust=False).mean()

    df["signal"] = 0

    # Compra quando a ema_short cruza acima da ema_long
    df.loc[df["ema_short"] > df["ema_long"], "signal"] = 1
    # Venda quando a ema_short cruza abaixo da ema_long
    df.loc[df["ema_short"] < df["ema_long"], "signal"] = -1

    return df

def backtest_ema(df, initial_capital=1000, fee_percent=0.001):
    """
    Realiza um backtest simples:
    - Entra comprado em sinal = 1 e sai quando sinal = -1
    - fee_percent => taxa de trade (ex: 0.1% => 0.001)
    
    Retorna:
    - df com colunas 'position', 'portfolio_value'
    - métricas finais (ROI)
    """
    df = df.copy()
    df["position"] = 0
    position = 0  # 1 = comprado, 0 = fora
    entry_price = 0
    capital = initial_capital
    shares = 0

    for i in range(1, len(df)):
        current_signal = df["signal"].iloc[i]
        close_price = df["close"].iloc[i]

        # Se não estamos em posição e o sinal é de compra, compramos
        if position == 0 and current_signal == 1:
            position = 1
            entry_price = close_price
            # Taxa do trade
            fee = capital * fee_percent
            # Montante após taxa
            capital_after_fee = capital - fee
            # Quantidade de shares compradas
            shares = capital_after_fee / close_price

        # Se estamos em posição e o sinal de venda apareceu, vendemos
        elif position == 1 and current_signal == -1:
            position = 0
            # Valor de venda
            sell_value = shares * close_price
            # Taxa do trade
            fee = sell_value * fee_percent
            capital = sell_value - fee
            shares = 0

        df["position"].iloc[i] = position

    # Se terminou em posição comprada, vendemos na última barra
    if position == 1:
        last_close = df["close"].iloc[-1]
        sell_value = shares * last_close
        fee = sell_value * fee_percent
        capital = sell_value - fee
        position = 0
        shares = 0

    # Adiciona coluna de valor de portfólio ao longo do tempo
    # Supondo que quando está comprado => capital investido + se valoriza 
    # e quando está fora => capital parado em "caixa"
    portfolio_values = []
    cap_temp = initial_capital
    pos = 0
    sh = 0
    entry_p = 0

    for i in range(len(df)):
        sig = df["signal"].iloc[i]
        c_price = df["close"].iloc[i]

        if i == 0:
            portfolio_values.append(cap_temp)
            continue

        if pos == 0 and sig == 1:
            pos = 1
            entry_p = c_price
            fee = cap_temp * fee_percent
            cap_temp -= fee
            sh = cap_temp / c_price
        elif pos == 1 and sig == -1:
            pos = 0
            sell_value = sh * c_price
            fee = sell_value * fee_percent
            cap_temp = sell_value - fee
            sh = 0

        # Se está comprado, valor é quantidade de shares * preço atual
        # Se está fora, valor é o próprio capital
        if pos == 1:
            portfolio_values.append(sh * c_price)
        else:
            portfolio_values.append(cap_temp)

    df["portfolio_value"] = portfolio_values
    # ROI final
    roi = (capital - initial_capital) / initial_capital * 100.0

    return df, roi

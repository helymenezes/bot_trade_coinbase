# arquivo: coinbase_trading.py
from coinbase.rest import RESTClient
from datetime import datetime, timedelta
import pandas as pd
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class CoinbaseTrading:
    def __init__(self):
        """
        Inicializa o cliente Coinbase Advanced Trading usando variáveis de ambiente
        """
        self.api_key = os.getenv('COINBASE_API_KEY')
        self.api_secret = os.getenv('COINBASE_API_SECRET')
        
        if not self.api_key or not self.api_secret:
            raise ValueError("As credenciais da API não foram encontradas no arquivo .env")
            
        self.client = RESTClient(api_key=self.api_key, api_secret=self.api_secret)
        
    # ... resto dos métodos permanecem iguais ...
    
    def get_market_data(self, product_id="BTC-USD", granularity=900, days_back=7):
        """
        Obtém dados históricos de mercado
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)
        
        candles = self.client.get_product_candles(
            product_id=product_id,
            start=start_time.isoformat(),
            end=end_time.isoformat(),
            granularity=granularity
        )
        
        df = pd.DataFrame(candles, columns=['start', 'high', 'low', 'open', 'close', 'volume'])
        df['start'] = pd.to_datetime(df['start'])
        return df
    
    # ... outros métodos da classe ...

# Exemplo de uso
if __name__ == "__main__":
    try:
        trading = CoinbaseTrading()
        
        # Exemplo de obtenção de dados de mercado
        btc_data = trading.get_market_data("BTC-USD", granularity=3600)
        print("\nDados de Mercado BTC-USD:")
        print(btc_data.head())
        
    except Exception as e:
        print(f"Erro: {e}")
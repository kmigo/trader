#import numpy as np
from dotenv import load_dotenv
load_dotenv()
import os,json
from binance import Client
import time
import pandas as pd

interval,historic  = '1h', "360 days ago UTC"
mean_min = 2
mean_min_column = f'SMA_{mean_min}'
mean_max = 4
mean_max_column = f'SMA_{mean_max}'
coins=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'DOGEUSDT', 'DOTUSDT', 'UNIUSDT', 'LTCUSDT', 'LINKUSDT', 'SOLUSDT','ETHUSDT']
main_coin ='ETHUSDT'
last_rsi = None
last_price = None
# Setup das chaves API da Binance
client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET'))

def get_historical_data(symbol, interval, start_str, end_str=None):
    bars = client.get_historical_klines(symbol, interval, start_str, end_str)
    df = pd.DataFrame(bars, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_time', 'Quote_av', 'Trades', 'Tb_base_av', 'Tb_quote_av', 'Ignore'])
    df['Close'] = pd.to_numeric(df['Close'])
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df.set_index('Timestamp', inplace=True)
    return df

def calculate_rsi(data, window=14):
    """Calcula o Relative Strength Index (RSI) para o dado DataFrame."""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def save_json(data, filename):
    if not filename.endswith('.json'):
        filename += '.json'

    with open(filename, 'w+') as f:
        json.dump(data, f,indent=4)

def load_json(filename):
    if not filename.endswith('.json'):
        filename += '.json'
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r') as f:
        data = json.load(f)
    return data 

def simulate_trades(df,coin):
    global last_price
     # valor total do portfólio
    data = load_json('trade_log.json')
    buy_prices = data.get('buy_prices', [])
    sell_prices = data.get('sell_prices', [])
    buy_indices = data.get('buy_indices', [])
    sell_indices = data.get('sell_indices', [])
    trade_log = data.get('trade_log', [])
    initial_value = data.get('initial_value', 10000)
    cash = data.get('cash', 10000)
    coins = data.get('coins', 0)
    portfolio = cash 

    date,row = df.iloc[-1].name,df.iloc[-1]
    if row['Position'] == 1 and cash > 0:  # sinal de compra
        coins = cash / row['Close']
        cash = 0
        buy_prices.append(row['Close'])
        buy_indices.append(str(date))  # Captura o índice do momento de compra
        trade_log.append((str(date), 'BUY', coins, row['Close']))
        print(f"+++++R$$$ Compra de {coin} em {date} por ${row['Close']:.2f}")
    elif row['Position'] == -1 and coins > 0:  # sinal de venda
        cash = coins * row['Close']
        coins = 0
        sell_prices.append(row['Close'])
        sell_indices.append(str(date))  # Captura o índice do momento de venda
        trade_log.append((str(date), 'SELL', coins, row['Close']))
        portfolio = cash
        print(f"----R$$$ Venda de {coin} em {date} por ${row['Close']:.2f}")
    print(f"Resultado do Portfólio para {coin}: ${portfolio:.2f}")
    print(f"cash inicial: ${initial_value:.2f}")
    print("resultado final: ",portfolio-initial_value)
    last_price=portfolio
    data['buy_prices'] = buy_prices
    data['sell_prices'] = sell_prices
    data['buy_indices'] = buy_indices
    data['sell_indices'] = sell_indices
    data['trade_log'] = trade_log
    data['initial_value'] = initial_value
    data['cash'] = cash
    data['coins'] = coins
    save_json(data, 'trade_log.json')
    return df, coin, buy_indices, buy_prices, sell_indices, sell_prices

def loop_coins(coin):
    global last_rsi
    try:
        df = get_historical_data(coin, interval, historic)
    except Exception as e:
        print(f"Erro ao carregar dados de {coin}: {e}")
        return None
    if df.empty:
        print("No data available for the specified period.")
    else:
        df[mean_min_column] = df['Close'].rolling(window=mean_min).mean()
        df[mean_max_column] = df['Close'].rolling(window=mean_max).mean()
        df['RSI'] = calculate_rsi(df['Close'], window=14)
        
        # Remova linhas onde mean_min_column, mean_max_column ou RSI são NaN
        df.dropna(subset=[mean_min_column, mean_max_column, 'RSI'], inplace=True)

        df['Signal'] = 0
        buy_signal = (df[mean_min_column] > df[mean_max_column]) & (df['RSI'] < 30)
        sell_signal = (df[mean_min_column] < df[mean_max_column]) & (df['RSI'] > 70)

        df.loc[buy_signal, 'Signal'] = 1
        df.loc[sell_signal, 'Signal'] = -1
        df['Position'] = df['Signal'].diff()
        # print ultimo rsi
        print(f"Ultimo RSI para {coin}: {df['RSI'].iloc[-1]:.2f}")
        last_rsi = df['RSI'].iloc[-1]
        return simulate_trades(df, coin)
    return None

while True:
    if last_rsi and last_price:
        print(f"Último RSI: {last_rsi:.2f}")
        print(f"Último valor do portfólio: ${last_price:.2f}")
        print('\n')
        print("#" * 60)
        print('\n')
    loop_coins(main_coin)
    time.sleep(15)
    os.system('cls' if os.name == 'nt' else 'clear')
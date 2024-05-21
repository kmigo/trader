from dotenv import load_dotenv
load_dotenv()
import os,math
from binance import Client
import datetime
import pandas as pd
import matplotlib.pyplot as plt
interval,historic  = '1h', "360 days ago UTC"
mean_min = 2
mean_min_column = f'SMA_{mean_min}'
mean_max = 4
mean_max_column = f'SMA_{mean_max}'
coins=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'DOGEUSDT', 'DOTUSDT', 'UNIUSDT', 'LTCUSDT', 'LINKUSDT', 'SOLUSDT']
main_coin ='BNBUSDT'
# Setup das chaves API da Binance
client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET'))

def simulate_trades(df,coin):
    cash = 10000  # capital inicial em dólares
    coins = 0  # quantidade de criptomoedas possuídas
    portfolio = cash  # valor total do portfólio
    buy_prices = []
    sell_prices = []
    buy_indices = []
    sell_indices = []
    trade_log = []

    for date, row in df.iterrows():
        if row['Position'] == 1 and cash > 0:  # sinal de compra
            coins = cash / row['Close']
            cash = 0
            buy_prices.append(row['Close'])
            buy_indices.append(date)  # Captura o índice do momento de compra
            trade_log.append((date, 'BUY', coins, row['Close']))
        elif row['Position'] == -1 and coins > 0:  # sinal de venda
            cash = coins * row['Close']
            coins = 0
            sell_prices.append(row['Close'])
            sell_indices.append(date)  # Captura o índice do momento de venda
            trade_log.append((date, 'SELL', coins, row['Close']))
            portfolio = cash
    print(f"Resultado do Portfólio para {coin}: ${portfolio:.2f}")
    return df, coin, buy_indices, buy_prices, sell_indices, sell_prices


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


def get_historical_data(symbol, interval, start_str, end_str=None):
    bars = client.get_historical_klines(symbol, interval, start_str, end_str)
    df = pd.DataFrame(bars, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_time', 'Quote_av', 'Trades', 'Tb_base_av', 'Tb_quote_av', 'Ignore'])
    df['Close'] = pd.to_numeric(df['Close'])
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df.set_index('Timestamp', inplace=True)
    return df

def loop_coins(coin):
    df = get_historical_data(coin,interval,historic )

    if df.empty:
        print("No data available for the specified period.")
    else:
        df[mean_min_column] = df['Close'].rolling(window=mean_min).mean()
        df[mean_max_column] = df['Close'].rolling(window=mean_max).mean()
        df['RSI'] = calculate_rsi(df['Close'], window=14)
        buy_signal = (df[mean_min_column] > df[mean_max_column]) & (df['RSI'] < 30)
        sell_signal = (df[mean_min_column] < df[mean_max_column]) & (df['RSI'] > 70)

        df.loc[buy_signal, 'Signal'] = 1
        df.loc[sell_signal, 'Signal'] = -1
        # Remova linhas onde mean_min_column ou mean_max_column são NaN
        df = df.dropna(subset=[mean_min_column, mean_max_column,'RSI'])
        df['Signal'] = 0
        df.loc[df[mean_min_column] > df[mean_max_column], 'Signal'] = 1
        df.loc[df[mean_min_column] < df[mean_max_column], 'Signal'] = -1
        df['Position'] = df['Signal'].diff()
        df = df.dropna(subset=['Position'])

        return  simulate_trades(df,coin)
    return None
    
def plot_chart(df, coin, buy_indices, buy_prices, sell_indices, sell_prices):
   # Ajuste na função de plotagem
    plt.figure(figsize=(12, 6))
    plt.plot(df['Close'], label='Preço de Fechamento', color='blue')
    plt.plot(df[mean_min_column], label='Média Móvel 20 dias', color='red')
    plt.plot(df[mean_max_column], label='Média Móvel 50 dias', color='green')

    # Assegura que as listas de índices e preços estão alinhadas
    if len(buy_indices) == len(buy_prices):
        plt.plot(buy_indices, buy_prices, '^', markersize=10, color='green', lw=0, label='Compra')

    if len(sell_indices) == len(sell_prices):
        plt.plot(sell_indices, sell_prices, 'v', markersize=10, color='red', lw=0, label='Venda')

    plt.title(f'Análise Técnica com Trades Simulados de {coin}')
    plt.xlabel('Data')
    plt.ylabel('Preço de Fechamento (USD)')
    plt.legend()
    plt.show()




def place_buy_order(symbol, quantity):
    """
    Coloca uma ordem de compra de mercado.
    """
    try:
        order = client.order_market_buy(
            symbol=symbol,
            quantity=quantity
        )
        print(f"Compra executada: {order}")
    except Exception as e:
        print(f"Erro ao executar a compra: {e}")

def place_sell_order(symbol, quantity):
    """
    Coloca uma ordem de venda de mercado.
    """
    try:
        order = client.order_market_sell(
            symbol=symbol,
            quantity=quantity
        )
        print(f"Venda executada: {order}")
    except Exception as e:
        print(f"Erro ao executar a venda: {e}")
        
def adjust_quantity(quantity, step_size):
    """Ajusta a quantidade para corresponder ao step size permitido."""
    precision = int(round(-math.log(step_size, 10), 0))
    return round(quantity - (quantity % step_size), precision)

def sell_all_position(symbol):
    """
    Vende toda a posição para um determinado ativo.
    """
    base_asset = symbol[:-4]  # Assume que o par termina com 'USDT'
    
    # Obter saldo disponível
    asset_balance = client.get_asset_balance(asset=base_asset)
    if asset_balance:
        quantity = float(asset_balance['free'])
        if quantity > 0:
            info = client.get_symbol_info(symbol)
            step_size = float([filt['stepSize'] for filt in info['filters'] if filt['filterType'] == 'LOT_SIZE'][0])
            adjusted_quantity = adjust_quantity(quantity, step_size)
            
            # Enviar ordem de venda de mercado
            try:
                order = place_sell_order(symbol=symbol, quantity=adjusted_quantity)
                print("Ordem de venda executada:", order)
            except Exception as e:
                print("Erro ao executar a venda:", e)
        else:
            print("Saldo insuficiente para venda.")
    else:
        print("Não foi possível obter o saldo do ativo.")

def get_min_notional_info(client, symbol):
    """
    Retorna o valor mínimo notional para um determinado par de moedas.
    """
    info = client.get_symbol_info(symbol)
    print(info)
    for filter in info['filters']:
        if filter['filterType'] == 'NOTIONAL':
            return float(filter['minNotional'])
    return None

def check_if_order_meets_notional(min_notional, quantity, price):
    """
    Verifica se a ordem atende ao valor notional mínimo.
    """
    notional_value = quantity * price
    return notional_value >= min_notional, notional_value

def execute_trade_in_binance():
    min_notional = get_min_notional_info(client, main_coin)
    print(f"Valor Notional Mínimo: {min_notional}")
    if min_notional:
        quantity = 0.04  # A quantidade que você deseja comprar ou vender
        current_price = float(client.get_symbol_ticker(symbol=main_coin)['price'])  # Obtém o preço atual
        meets_notional, notional_value = check_if_order_meets_notional(min_notional, quantity, current_price)
        print(f"Valor Notional da Ordem: {notional_value}, Atende ao mínimo? {meets_notional}")

        if not meets_notional:
            print("A ordem não atende ao valor notional mínimo. Ajuste a quantidade ou o preço.")
        else:

            sell_all_position(main_coin)

if (params:=loop_coins(main_coin)):
    plot_chart(*params)

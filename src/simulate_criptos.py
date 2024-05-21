import pandas as pd
import pandas_datareader.data as web
import matplotlib.pyplot as plt
import datetime

def simulate_trades(df):
    cash = 10000  # capital inicial em dólares
    coins = 0  # quantidade de criptomoedas possuídas
    portfolio = cash  # valor total do portfólio
    buy_prices = []
    sell_prices = []
    trade_log = []

    for date, row in df.iterrows():
        if row['Position'] == 1:  # sinal de compra
            if cash > 0:  # só compra se tiver cash disponível
                coins = cash / row['Close']
                cash = 0
                buy_prices.append(row['Close'])
                trade_log.append((date, 'BUY', coins, row['Close']))
        elif row['Position'] == -1:  # sinal de venda
            if coins > 0:  # só vende se tiver moedas
                cash = coins * row['Close']
                coins = 0
                sell_prices.append(row['Close'])
                trade_log.append((date, 'SELL', coins, row['Close']))
                portfolio = cash
    
    return trade_log, portfolio, buy_prices, sell_prices

# Definir as datas de início e fim da análise
start = datetime.datetime(2020, 1, 1)
end = datetime.datetime.now()

# Carregar dados da criptomoeda Bitcoin
df = web.DataReader('BTC-USD', 'yahoo', start, end)

# Calcular médias móveis simples de 20 e 50 dias
df['SMA_20'] = df['Close'].rolling(window=20).mean()
df['SMA_50'] = df['Close'].rolling(window=50).mean()

# Identificar os cruzamentos de alta e de baixa
df['Signal'] = 0
df['Signal'][df['SMA_20'] > df['SMA_50']] = 1
df['Signal'][df['SMA_20'] < df['SMA_50']] = -1
df['Position'] = df['Signal'].diff()

# Simular trades e obter o log de trades e o resultado do portfólio
trade_log, final_portfolio, buy_prices, sell_prices = simulate_trades(df)

# Plotar os preços de fechamento, médias móveis e sinais de compra/venda
plt.figure(figsize=(12, 6))
plt.plot(df['Close'], label='Preço de Fechamento BTC', color='blue')
plt.plot(df['SMA_20'], label='Média Móvel 20 dias', color='red')
plt.plot(df['SMA_50'], label='Média Móvel 50 dias', color='green')
plt.plot(df[df['Position'] == 1].index, buy_prices, '^', markersize=10, color='g', lw=0, label='Compra')
plt.plot(df[df['Position'] == -1].index, sell_prices, 'v', markersize=10, color='r', lw=0, label='Venda')
plt.title('Análise Técnica com Trades Simulados de Bitcoin')
plt.xlabel('Data')
plt.ylabel('Preço de Fechamento (USD)')
plt.legend()
plt.show()

# Imprimir resultados dos trades e o valor final do portfólio
print("Log de Trades:", trade_log)
print("Valor final do portfólio:", final_portfolio)

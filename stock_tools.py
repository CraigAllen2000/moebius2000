import pandas as pd
import numpy as np
import requests
import json
import datetime

def getPriceHistory(stock_ticker, dates, freq='daily'):#,periodType='year',period=1,frequencyType='daily',frequency=1):
    start = round(dates[0].timestamp())*1000
    end = round(dates[1].timestamp())*1000
    td_consumer_key = '2QG3VO3MTWMSKGS4XCWQJAOSPUT3UR6R'
    endpoint = 'https://api.tdameritrade.com/v1/marketdata/{stock_ticker}/pricehistory?periodType={periodType}&frequencyType={frequencyType}&startDate={startDate}&endDate={endDate}'#periodType={periodType}
    #full_url = endpoint.format(stock_ticker=stock_ticker,periodType=periodType,period=period,frequencyType=frequencyType,frequency=frequency)#,startDate=startDate,endDate=endDate
    full_url = endpoint.format(stock_ticker=stock_ticker,periodType='year',frequencyType=freq,startDate=start,endDate=end)#periodType='year'
    page = requests.get(url=full_url,
                        params={'apikey' : td_consumer_key})
    content = json.loads(page.content)['candles']
    df = pd.DataFrame(content)
    n = len(content)
    data = np.zeros((n,6))
    for i in range(n):
        data[i,:] = [content[i]['open'],content[i]['high'],content[i]['low'],content[i]['close'],content[i]['volume'],content[i]['datetime']]
    return data, df

def sma(data,k):
    n = data.shape[0]
    means = np.zeros(n)
    for i in range(n):
        if i>k:
            means[i] = np.mean(data[i-k+1:i+1])
        else:
            means[i] = np.mean(data[:i+1])
    return means

def emma(data,N=14):
    n = len(data)
    emmas = np.ones(n)*data[0]
    for i in range(n):
        if i>1:
            a = 2/(N+1)
            emmas[i] = a*data[i]+(1-a)*emmas[i-1]
    return emmas

def convert_time(array):
    dates = []
    for i in range(len(array)):
        dates.append(datetime.datetime.fromtimestamp(array[i] / 1e3))
    return np.array(dates)

def roll_std(data,k):
    n = data.shape[0]
    stds = np.zeros(n)
    for i in range(n):
        if i>k:
            stds[i] = np.std(data[i-k+1:i+1])
        else:
            stds[i] = np.std(data[:i+1])
    return stds

def get_Bands(data,p1=20,p2=2):
    n = data.shape[0]
    stds = np.array(roll_std(data,p1))
    means = np.array(sma(data,p1))
    return means-p2*stds,means+p2*stds

class Account:
    def __init__(self, cash, shares):
        self.cash = cash
        self.shares = shares
    def market_buy(self, nshares, price):
        net_cost = nshares*price
        #print('Bought: ',nshares,' shares for $',price,'/share')
        self.cash -= net_cost
        self.shares += nshares
    def market_sell(self, nshares, price):
        net_cost = nshares*price
        #print('Sold: ',nshares,' shares for $',price,'/share')
        self.cash += net_cost
        self.shares -= nshares
    def balance(self, price):
        invested = self.shares*price
        return self.cash,self.shares,invested
    
class RSI_rule:
    def __init__(self, df, upper_profit=1.50, lower_loss=0.90):
        self.rsi = emma(getRSI(df['close']))
    def check(self, t, account, price):
        
        if self.rsi[t] < 40 and account.cash > 0:
            return "BUY"
        elif self.rsi[t] > 60 and account.shares > 0:
            return "SELL"
        else:
            return "HOLD"

class MACD_rule:
    def __init__(self, df, upper_profit=1.50, lower_loss=0.90):
        self.MACDslow, self.MACDfast, self.MACDhist = getMACD(df['close'])
        self.up = upper_profit
        self.ll = lower_loss
    def check(self, t, account, price):
        value = findIntersect(self.MACDhist, t)
        if value == 1 and account.cash > 0:
            return "BUY"
        elif value == 2 and account.shares > 0:
            return "SELL"
        else:
            return "HOLD"

class EMMA_rule:
    def __init__(self, df_wk, upper_profit=1.50, lower_loss=0.90, k=2):
        self.emma = emma(df_wk['close'])
        self.up = upper_profit
        self.ll = lower_loss
        self.k = k
    def check(self, t, account, price):
        slope = (self.emma[t]-self.emma[t-self.k])/self.k
        if slope >= 0 and account.cash > 0:
            return "BUY"
        elif slope < 0 and account.shares > 0:
            return "SELL"
        else:
            return "HOLD"

def getUD(data): #use with close prices
    n = len(data)
    U = np.ones(n)*0.0000001
    D = np.ones(n)*0.0000001
    for i in range(n):
        if i>0:
            if data[i]>data[i-1]:
                U[i] = data[i]-data[i-1]
                D[i] = 0
            elif data[i]<data[i-1]:
                D[i] = data[i-1]-data[i]
                U[i] = 0
            else:
                U[i] = 0
                D[i] = 0
    return U,D

def getRSI(data): #use with close prices
    n=len(data)
    U,D = getUD(data)
    RS = emma(U)/emma(D)
    RSI = 100-100/(1+RS)
    return RSI

def getMACD(data,p1=12,p2=26):
    fast = emma(data,p1)-emma(data,p2)
    slow = emma(fast,9)
    hist = fast-slow
    return slow,fast,hist

def getAD(df):
    n = len(df)
    AD = np.zeros(n)
    AD[0] = (df['close'][0]-df['open'][0])*df['volume'][0]/(df['high'][0]-df['low'][0])
    for i in range(n-1):
        j = i+1
        AD[j] = AD[j-1] + (df['close'][j]-df['open'][j])*df['volume'][j]/(df['high'][j]-df['low'][j])
    return AD
def getMinorLow(df,t,period=5):
    if t>4:
        return min(df['close'][t-1-period:t-1])
    else: return df['close'][t]
    
def getMinorHigh(df,t,period=5):
    if t>4:
        return max(df['close'][t-1-period:t-1])
    else: return df['close'][t]

def findIntersect(hist, t, tol=0.01):
    if t>0:
            if hist[t-1]+tol < 0 and hist[t]-tol > 0:
                return 1
            elif hist[t-1]-tol > 0 and hist[t]+tol < 0:
                return 2
            else:
                return 0
    else:
        return 0
    
def findAllIntersects(hist,tol=0.01):
    n = len(hist)
    res = np.zeros(n)
    for i in range(n):
        if i>0:
            if hist[i-1]+tol < 0 and hist[i]-tol > 0:
                res[i] = 1
            elif hist[i-1]-tol > 0 and hist[i]+tol < 0:
                res[i] = 2
    return res

def runSimulation(df,Rule,wait_time,capital,bp,sp,prnt=True):

    trade_log = np.zeros(len(df))
    a1 = Account(capital,0)
    rule = Rule(df,bp,sp)
    upper_profit = -1
    lower_loss = -1
    
    for t_p in range(len(df)-wait_time):
        t = t_p + wait_time

        price = df['close'][t]
        date = datetime.datetime.fromtimestamp(df['datetime'][t] / 1e3)
        shares_to_sell = a1.shares
        shares_to_buy = a1.cash//price
        
        signal = rule.check(t,a1,price)
        
        if signal == "BUY" and shares_to_buy > 0:
            if prnt: print(date,": Bought.","\n")
            a1.market_buy(shares_to_buy,price)
            trade_log[t] = 1
            continue
        elif signal == "SELL" and shares_to_sell > 0:
            if prnt: print(date,": Sold.","\n")
            a1.market_sell(shares_to_sell,price)
            trade_log[t] = 2
            continue
        else:
            continue
            
    return trade_log, a1.balance(df['close'][len(df)-1])

import vectorbt as vbt
import pandas as pd
import numpy as np
import talib
import datetime as dt
from ta.trend import STCIndicator
#!/usr/bin/env python3
from kite_trade import *
from indicators import MACD,vwap
from supertrend_kite import *

import datetime,calendar
import pandas as pd
import itertools 
import math
from datetime import datetime as dt
import time
import json,copy
import requests
import time
from pytz import timezone
from datetime import datetime, time

from functions import *

import warnings,random

def indicator_data(df,date):
    data = [[x['date'],x['open'],x['high'],x['low'],x['close'],x['volume'],] for x in df]
    dg= {}
    dg["data"]={}
    dg["data"]["candles"]=data
    df = pd.DataFrame(dg["data"]["candles"], columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    # df['signal'] = df.apply(lambda row: 1 if row['Close'] >= row['Open'] else -1, axis=1)
    df['SMA_20_Volume'] = df['Volume'].rolling(window=20).mean()
    df=df[df["Date"].dt.date==date]
    
    last_candle=df.iloc[-1]
    first_candle =df.iloc[0]
    vol_crit = (last_candle["Volume"]>=4*last_candle["SMA_20_Volume"]) and (last_candle["Volume"]>500000)
    mov_crit = ((last_candle["Close"]/first_candle["Open"])-1)>=0.02
    
    
    
    
    
    return mov_crit and vol_crit , last_candle["Close"]




def get_tail_time():
    from datetime import datetime, timedelta
    now = datetime.now()
    # Calculate the next multiple of 15 minutes
    next_15_min = (now.minute // 15 + 1) * 15
    # Calculate the target time for the next 15-minute interval
    if next_15_min == 60:
        target_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        target_time = now.replace(minute=next_15_min, second=0, microsecond=0)
    # Calculate the remaining time to the next 15-minute interval
    remaining_time = target_time - now
    # Get the remaining seconds
    seconds_to_next = remaining_time.total_seconds()
    return seconds_to_next,now.time(),now.date()




warnings.simplefilter(action='ignore', category=RuntimeWarning)


enctoken = open('token.txt','r').read() # "UAg73k1S7/4E3ek1acjp6dWAPZWAr3Y4HKNIjfHyFRmEYv0EhV9szZ+hPYJCRywhr6Gs3Tk63dQfM2YT6cEr0CqKDHloUAAxacVwbv2PuZI7X+rlBVchYw=="
kite = KiteApp(enctoken=enctoken)
#kite = login()
logged_in=1
timestamp=0
target_frac=1
candle_cutoff=pd.to_datetime('13:31:00').time()# pd.to_datetime('11:00:00').time()
trade_check = pd.to_datetime('11:15:00').time()#pd.to_datetime('11:15:00').time()
square_off_time = pd.to_datetime('15:11:00').time()

day_start =  pd.to_datetime('9:25:00').time()
day_end=  pd.to_datetime('15:30:00').time()


final_list = pd.read_csv("screener_stocks.csv")
final_list =final_list[final_list["leverage"]==5]['stocks'].tolist()

stock_keys=kite.instruments("NSE")
stock_list =final_list

dict_stock={}

for i in stock_list[0:200]:
    if i not in ["FOCUS","COFFEEDAY","DONEAR","ISMTLTD","LIBERTSHOE","BIRLAMONEY","INDSWFTLAB","AURUM"]:
        dict_stock[i]= [x["instrument_token"]  for x in stock_keys if x["tradingsymbol"]==i][0]

swapped_dict_stock = {value: key for key, value in dict_stock.items()}

stock_codes = list(dict_stock.values())

from_datetime = datetime.datetime.now() - datetime.timedelta(days=2)    # From last & days


to_datetime = datetime.datetime.now()


start_time = time.time()
time_end,time_now,date= get_tail_time()
for i in list(dict_stock.values())[0:200]:
    df = indicator_data(kite.historical_data(i, from_datetime,to_datetime, "15minute", continuous=False, oi=False),date)
    print(i)
end_time = time.time()
time_gap = end_time - start_time
print(round(time_gap,2))

ready_to_trade=[]
traded =[]
sl_target=[]
while 1:
    # print(from_datetime)
    try:
        time_end,time_now,date= get_tail_time()
        if  time_end<25 and time_end>23 and time_now<=candle_cutoff and time_now>=day_start:
            ready_to_trade=[]
            to_datetime = datetime.datetime.now()
            stock_codes_iter = copy.deepcopy(stock_codes)
            for i in stock_codes_iter:
                trade,close = indicator_data(kite.historical_data(i, from_datetime,to_datetime, "15minute", continuous=False, oi=False),date)
                if trade:
                    stock_codes.remove(i)
                    ready_to_trade.append([i,close])
                    print(swapped_dict_stock[i],time_end)
            
        if time_end<3 or time_end>897:
            ready_to_trade_iter = copy.deepcopy(ready_to_trade)    
            for i in ready_to_trade_iter:
                key =swapped_dict_stock[i[0]]
                qty = int(5*2100/i[1])
                oid_sell = place_order_kite(kite,key,qty,sell_buy="SELL")
                traded.append(oid_sell)
                print(key,"place short order here immediately based on the position sizing calculated at the begining of the day itself")
                ready_to_trade.remove(i)
                
                # print("remove that stock from dictionary maintain a separate dictionary")
                    
            
        
        if int(time_end)%5==3 and time_end>20 and time_end<888: # check every 30s the status of sell and buy and SL orders and update accordingly
            a = (time_now>= trade_check) #post 11:15 then yes else no
            traded_iter = copy.deepcopy(traded) 
            for oid in traded_iter:
                price, quantity,status,key = get_order_status_meta(kite, oid) #value  is amount of stock traded in Rs. if traded else will be False
                if status=="COMPLETE":            
                    oid_sl = place_order_kite_sl(round(price*1.01/0.05)*0.05,kite,key,quantity,sell_buy="BUY")
                    oid_sell = place_order_kite_price(round(price*0.985/0.05)*0.05,kite,key,quantity,sell_buy="BUY")
                    sl_target.append([oid_sell,oid_sl])
                    traded.remove(oid)
                    time.sleep(3)
                    print(key,"SL and Target orders placed")
                else:
                    traded.remove(oid)
            # time.sleep(1)
                    
                
        if int(time_end)%7==1 and time_end>20 and time_end<860:#time_now>=square_off_time: # check at 15:10  # Follow-up check if any of the orders got declined or were not placed then this will break
            sl_target_iter = copy.deepcopy(sl_target) 
            for i in sl_target_iter:
                try:
                    price, quantity,status,key = get_order_status_meta(kite, i[0])
                    price_sl, quantity_sl,status_sl,key_sl = get_order_status_meta(kite, i[1])
                    # print(status,status_sl)
                    if status=="COMPLETE": 
                        print("close SL order")
                        cancel_order = kite.cancel_order('regular',i[1])
                        sl_target.remove(i)
                    elif status_sl=="COMPLETE":
                        print("close target order")
                        cancel_order = kite.cancel_order('regular',i[0])
                        sl_target.remove(i)
                    elif time_now>=square_off_time:
                        print("square off at market price and then also close these existing SL and target orders")
                        cancel_order = kite.cancel_order('regular',i[0])
                        cancel_order = kite.cancel_order('regular',i[1])
                        place_order_kite(kite,key,quantity,sell_buy="BUY") # replace key with stock symbol, somehow
                        sl_target.remove(i)
                except:
                    print("error in SL, exit order status check block, sleeping")
                    time.sleep(1)
                    enctoken = open('token.txt','r').read() # "UAg73k1S7/4E3ek1acjp6dWAPZWAr3Y4HKNIjfHyFRmEYv0EhV9szZ+hPYJCRywhr6Gs3Tk63dQfM2YT6cEr0CqKDHloUAAxacVwbv2PuZI7X+rlBVchYw=="
                    kite = KiteApp(enctoken=enctoken)
                  
                    
            # print("ending the day with squaring off  all stocks")
            # time.sleep(60*60)
            
                    
        
        while time_now<=day_start or time_now>=day_end:# or datetime.now().weekday()==5 or datetime.now().weekday()==6:
            time_end,time_now,date= get_tail_time()
            print("sleeping")
            time.sleep(60)
            enctoken = open('token.txt','r').read() # "UAg73k1S7/4E3ek1acjp6dWAPZWAr3Y4HKNIjfHyFRmEYv0EhV9szZ+hPYJCRywhr6Gs3Tk63dQfM2YT6cEr0CqKDHloUAAxacVwbv2PuZI7X+rlBVchYw=="
            kite = KiteApp(enctoken=enctoken)
    except:
        print("some error somewhere")
        time.sleep(3)
        enctoken = open('token.txt','r').read() # "UAg73k1S7/4E3ek1acjp6dWAPZWAr3Y4HKNIjfHyFRmEYv0EhV9szZ+hPYJCRywhr6Gs3Tk63dQfM2YT6cEr0CqKDHloUAAxacVwbv2PuZI7X+rlBVchYw=="
        kite = KiteApp(enctoken=enctoken)
            
            
            
            
            
            
            
            
            
            
            
# oid_sell = place_order_kite_sl(capital[key][3],kite,key,capital[key][6],sell_buy="SELL")
# value, quantity = get_order_status(kite,capital[key][7])
            
            
            
            
            
            
            
            
            
            
            
            
            
        
            
            
            
            
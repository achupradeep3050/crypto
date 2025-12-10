from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import uvicorn
import os

app = FastAPI(title="MT5 Windows Agent")

# Pydantic models for request bodies
class TradeRequest(BaseModel):
    symbol: str
    action: str  # "buy" or "sell"
    volume: float
    price: float  # Limit price
    sl: float
    tp: float
    order_type: str = "limit" # "limit" or "market"

class InitResponse(BaseModel):
    status: bool
    version: tuple
    terminal_info: dict

@app.get("/")
def read_root():
    return {"status": "running", "service": "MT5 Agent"}

@app.post("/init")
def initialize_mt5():
    if not mt5.initialize():
        raise HTTPException(status_code=500, detail=f"initialize() failed, error code = {mt5.last_error()}")
    
    version = mt5.version()
    terminal_info = mt5.terminal_info()._asdict()
    return {"status": True, "version": version, "terminal_info": terminal_info}

@app.get("/account")
def get_account_info():
    if not mt5.initialize():
         raise HTTPException(status_code=500, detail="MT5 not initialized")
    
    account_info = mt5.account_info()
    if account_info is None:
        raise HTTPException(status_code=500, detail="Failed to get account info")
    
    return account_info._asdict()

@app.get("/data/{symbol}/{timeframe}")
def get_candles(symbol: str, timeframe: str, n: int = 100):
    if not mt5.initialize():
         raise HTTPException(status_code=500, detail="MT5 not initialized")
    
    # Map timeframe string to MT5 constant
    tf_map = {
        "1m": mt5.TIMEFRAME_M1,
        "5m": mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15,
        "1h": mt5.TIMEFRAME_H1,
        "4h": mt5.TIMEFRAME_H4,
        "1d": mt5.TIMEFRAME_D1,
    }
    
    mt5_tf = tf_map.get(timeframe)
    if mt5_tf is None:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")
    
    rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, n)
    if rates is None:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        
    # Convert to list of dicts for JSON
    data = []
    for rate in rates:
        data.append({
            "time": int(rate['time']), # Unix timestamp
            "open": float(rate['open']),
            "high": float(rate['high']),
            "low": float(rate['low']),
            "close": float(rate['close']),
            "tick_volume": int(rate['tick_volume']),
        })
    
    return data

@app.post("/trade")
def execute_trade(trade: TradeRequest):
    if not mt5.initialize():
         raise HTTPException(status_code=500, detail="MT5 not initialized")
    
    symbol_info = mt5.symbol_info(trade.symbol)
    if symbol_info is None:
        raise HTTPException(status_code=404, detail=f"{trade.symbol} not found")
    
    if not symbol_info.visible:
        if not mt5.symbol_select(trade.symbol, True):
            raise HTTPException(status_code=404, detail=f"{trade.symbol} not found or not visible")

    digits = symbol_info.digits
    
    # Determine Order Type
    action = mt5.TRADE_ACTION_PENDING
    type_order = mt5.ORDER_TYPE_BUY_LIMIT if trade.action == "buy" else mt5.ORDER_TYPE_SELL_LIMIT
    price = trade.price
    
    if trade.order_type == "market":
        action = mt5.TRADE_ACTION_DEAL
        type_order = mt5.ORDER_TYPE_BUY if trade.action == "buy" else mt5.ORDER_TYPE_SELL
        # For Market, we must use current Ask/Bid
        price = symbol_info.ask if trade.action == "buy" else symbol_info.bid
    
    request = {
        "action": action,
        "symbol": trade.symbol,
        "volume": trade.volume,
        "type": type_order,
        "price": round(price, digits),
        "sl": round(trade.sl, digits),
        "tp": round(trade.tp, digits),
        "deviation": trade.deviation,
        "magic": 234000,
        "comment": "MeanReversalRSI Bot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN, # Fill or Kill often fails, Return is safer
    }
    
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE: 
        raise HTTPException(status_code=500, detail=f"Order failed: {result.comment}")
        
    return result._asdict()

if __name__ == "__main__":
    # Host 0.0.0.0 is important to be accessible from the Ubuntu host
    uvicorn.run(app, host="0.0.0.0", port=8001)

from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from contextlib import asynccontextmanager
import logging
import aiohttp
import pandas as pd


from backend.strategy_engine import StrategyEngine
from backend.config import settings
from backend.backtest_engine import BacktestEngine


# from strategy.TMA.tma_strategy import TMAStrategy - REMOVED
# from strategy.mean_reversion import MeanReversionRSI - REMOVED
from strategy.BitcoinBreakout.bitcoin_breakout import BitcoinBreakout
import os
from datetime import datetime




# Instantiate Strategies

# 1. MEAN REVERSION (REMOVED)
# 2. TMA SYSTEM (REMOVED)

# 3. BITCOIN BREAKOUT (New High ROI)
engine_btc_breakout_5m = StrategyEngine(name="BTC_BREAKOUT_5M", mode="BTC_BREAKOUT_5M", log_file="logs/Breakout/5m.log", strategy_class=BitcoinBreakout, symbols=["BITCOIN"])

# 4. GOLD Strategies (Existing)
# 4. GOLD Strategies (New High Performance)
from strategy.Gold.gold_trend import GoldTrend
from strategy.Gold.gold_flux import GoldFlux
from strategy.Gold.gold_sniper import GoldSniper

engine_gold_1h = StrategyEngine(name="GOLD_1H", mode="GOLD_1H", log_file="logs/GOLD/1h.log", strategy_class=GoldTrend, symbols=["GOLD"])

# Gold Sniper (High Precision, Mean Reversion)
engine_gold_15m = StrategyEngine(
    name="GOLD_SNIPER_15m",
    mode="GOLD_15M",
    log_file="logs/GOLD/sniper_15m.log",
    strategy_class=GoldSniper, 
    symbols=["GOLD"]
)

# Gold Flux (Momentum Scalp) - Keeping as secondary
engine_gold_5m = StrategyEngine(
    name="GOLD_FLUX_5M",
    mode="GOLD_5M",
    log_file="logs/GOLD/flux_5m.log",
    strategy_class=GoldFlux, 
    symbols=["GOLD"]
)

# Global loop controller
loop_active = True

async def monitor_account():
    '''Independent loop to fetch account info regardless of strategy status'''
    while loop_active:
        async with aiohttp.ClientSession() as session:
             # Use one engine to update account info (Shared)
             await engine_btc_breakout_5m.update_account_info(session)
        await asyncio.sleep(5)

async def bot_background_loop():
    while loop_active:
        tasks = []
        # Mean Reversion REMOVED
        
        # TMA REMOVED
        
        # Bitcoin Breakout
        if engine_btc_breakout_5m.active: tasks.append(engine_btc_breakout_5m.run_loop())

        # Gold
        if engine_gold_1h.active: tasks.append(engine_gold_1h.run_loop())
        if engine_gold_15m.active: tasks.append(engine_gold_15m.run_loop())
        if engine_gold_5m.active: tasks.append(engine_gold_5m.run_loop())
            
        if tasks:
            await asyncio.gather(*tasks)
            
        await asyncio.sleep(10) # Run every 10 seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    asyncio.create_task(bot_background_loop())
    asyncio.create_task(monitor_account())
    
    yield
    
    # Shutdown
    print("[SYSTEM] Shutting Down...")
    global loop_active
    loop_active = False
    task.cancel()

app = FastAPI(lifespan=lifespan)

# Enable CORS for Django Frontend (Port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.00.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="web_dashboard/core/static"), name="static")
templates = Jinja2Templates(directory="web_dashboard/core/templates/core")

# Client Logging Endpoint
class ClientLogRequest(BaseModel):
    level: str
    message: str
    context: dict = {}

@app.post("/api/client_log")
async def client_log(req: ClientLogRequest):
    log_file = "logs/client_transition.log"
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] [{req.level.upper()}] {req.message} | Context: {req.context}\n")
    return {"status": "logged"}

class AgentLogRequest(BaseModel):
    level: str
    message: str
    context: dict = {}

@app.post("/api/agent/log")
async def agent_log(req: AgentLogRequest):
    log_file = "logs/agent_remote.log"
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{req.level.upper()}] {req.message} | Context: {req.context}\n"
    
    # Write to file
    with open(log_file, "a") as f:
        f.write(log_entry)
        
    # Also print to console for immediate visibility
    print(f"xx [AGENT] {log_entry.strip()}")
    
    return {"status": "logged"}

# Enable CORS for Django Frontend (Port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.00.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="web_dashboard/core/static"), name="static")
templates = Jinja2Templates(directory="web_dashboard/core/templates/core")

class ControlRequest(BaseModel):
    action: str
    target: str = "all" # "swing", "scalp", "tma", "all"

class TestTradeRequest(BaseModel):
    strategy: str
    symbol: str
    action: str # "long" or "short"
    order_type: str = "market" # "market" or "limit"

# ... (skip lines)

@app.post("/api/test_trade")
async def test_trade(req: TestTradeRequest):
    target_engine = None
    # Update logic to match new engines
    s = req.strategy.lower()
    if s == "mr_1h": pass
    elif s == "gold_1h": target_engine = engine_gold_1h
    elif s == "gold_15m": target_engine = engine_gold_15m
    elif s == "gold_5m": target_engine = engine_gold_5m
    elif s == "btc_breakout_5m": target_engine = engine_btc_breakout_5m
    
    if target_engine:
        async with aiohttp.ClientSession() as session:
            # 1. Fetch Real Price
            # Use engine's configured current timeframe or just 1m for price check
            df = await target_engine.fetch_candles(session, req.symbol, "1m")
            if df is None or df.empty:
                return {"status": "error", "message": f"Could not fetch price for {req.symbol}"}
            
            current_price = float(df['close'].iloc[-1])
            
            # 2. Calculate Params
            # Limit: Safe OTM. Market: At Market.
            entry = current_price
            if req.order_type == "limit":
                 # Place 'Pending' order far away to guarantee acceptance without fill
                 # Long: 0.9 * Price. Short: 1.1 * Price
                 if req.action == "long": entry = current_price * 0.95
                 else: entry = current_price * 1.05
            
            # SL/TP just for validation
            sl = entry * 0.90 if req.action == "long" else entry * 1.10
            tp = entry * 1.10 if req.action == "long" else entry * 0.90
            
            # 3. Execute
            await target_engine.execute_trade(session, req.symbol, req.action, entry, sl, tp, order_type=req.order_type)
            return {
                "status": f"Trade Sent ({req.order_type})", 
                "strategy": req.strategy, 
                "details": f"Price={entry:.2f}"
            }

class SettingsRequest(BaseModel):
    agent_url: str
    risk: float

@app.get("/")
def read_root(request: Request):
    import traceback
    try:
        return templates.TemplateResponse("home.html", {"request": request})
    except Exception as e:
        with open("logs/root_error.txt", "w") as f:
            f.write(traceback.format_exc())
        raise e

@app.get("/mean_reversion")
def read_mean_reversion(request: Request):
    return templates.TemplateResponse("mean_reversion.html", {"request": request})

@app.get("/tma")
def read_tma(request: Request):
    return templates.TemplateResponse("tma.html", {"request": request})

@app.get("/backtest")
def read_backtest(request: Request):
    return templates.TemplateResponse("backtest.html", {"request": request})

@app.get("/api/status")
def get_status():
    return {
        "mean_reversion": {},
        "tma": {},
        "btc_breakout_5m": {
             "active": engine_btc_breakout_5m.active, 
             "status": engine_btc_breakout_5m.status, 
             "data": engine_btc_breakout_5m.market_data, 
             "logs": engine_btc_breakout_5m.logs[:20]
        },
        "gold": {
            "1h": {"active": engine_gold_1h.active, "status": engine_gold_1h.status, "data": engine_gold_1h.market_data, "logs": engine_gold_1h.logs[:20]},
            "15m": {"active": engine_gold_15m.active, "status": engine_gold_15m.status, "data": engine_gold_15m.market_data, "logs": engine_gold_15m.logs[:20]},
            "5m": {"active": engine_gold_5m.active, "status": engine_gold_5m.status, "data": engine_gold_5m.market_data, "logs": engine_gold_5m.logs[:20]},
        },
        "account": engine_btc_breakout_5m.account_info, 
        "config": {
            "agent_url": engine_btc_breakout_5m.agent_url,
            "risk": settings.RISK_PERCENT,
            "telegram_connected": bool(engine_btc_breakout_5m.notifier and engine_btc_breakout_5m.notifier.chat_id)
        }
    }


@app.post("/api/control")
async def control_bot(req: ControlRequest):
    if req.action == "start":
        # Mean Reversion & TMA Logic Removed
        
        # Breakout Control
        if req.target == "btc_breakout_5m": engine_btc_breakout_5m.start()
        
        # Gold Support
        if req.target in ["gold", "all"]:
            engine_gold_1h.start()
            engine_gold_15m.start()
            engine_gold_5m.start()
        elif req.target == "gold_1h": engine_gold_1h.start()
        elif req.target == "gold_15m": engine_gold_15m.start()
        elif req.target == "gold_5m": engine_gold_5m.start()
            
    elif req.action == "stop":
        # Mean Reversion & TMA Logic Removed

        # Breakout Control
        if req.target == "btc_breakout_5m": engine_btc_breakout_5m.stop()

        # Gold Support
        if req.target in ["gold", "all"]:
            engine_gold_1h.stop()
            engine_gold_15m.stop()
            engine_gold_5m.stop()
        elif req.target == "gold_1h": engine_gold_1h.stop()
        elif req.target == "gold_15m": engine_gold_15m.stop()
        elif req.target == "gold_5m": engine_gold_5m.stop()
            
    return {"status": "ok"}


def update_env_file(key, value):
    env_path = ".env"
    lines = []
    found = False
    
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
            
    with open(env_path, "w") as f:
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}=\"{value}\"\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f"{key}=\"{value}\"\n")

class BacktestRequest(BaseModel):
    strategy: str
    symbol: str
    timeframe: str
    balance: float
    days: int

@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    import traceback
    try:
        # 1. Fetch Data
        engine = BacktestEngine(agent_url=engine_btc_breakout_5m.agent_url)
        # Calculate timestamps (From Yesterday Backwards)
        now = datetime.now()
        yesterday = now - pd.Timedelta(days=1)
        end_ts = int(yesterday.timestamp())
        start_ts = int((yesterday - pd.Timedelta(days=req.days)).timestamp())
        
        # Log for debugging
        print(f"Backtest: {req.symbol} {req.timeframe} Days={req.days} (From {yesterday.date()} back)")
        
        df = await engine.get_data(req.symbol, req.timeframe, start_ts, end_ts)

        if df.empty:
            return {"error": "No data found for this period."}
            
        # 2. Select Strategy
        strat = None
        if req.strategy == "BitcoinBreakout": strat = BitcoinBreakout
        # Gold Strategies
        elif req.strategy == "GoldTrend": strat = GoldTrend
        elif req.strategy == "GoldSniper": strat = GoldSniper
        elif req.strategy == "GoldFlux": strat = GoldFlux
        
        if not strat: return {"error": "Invalid Strategy"}
        
        # 3. Run Simulation
        result = engine.run(strat, df, start_balance=req.balance)
        return result
    except Exception as e:
        err_msg = traceback.format_exc()
        with open("logs/backtest_error.log", "w") as f:
            f.write(err_msg)
        return {"error": f"Internal Error: {str(e)}"}

@app.post("/api/settings")
def update_settings(req: SettingsRequest):
    # 1. Update In-Memory Config (Immediate Effect)
    # Mean Reversion & TMA Removed
    # Breakout
    engine_btc_breakout_5m.set_agent_url(req.agent_url)
    # Gold
    engine_gold_1h.set_agent_url(req.agent_url)
    engine_gold_15m.set_agent_url(req.agent_url)
    engine_gold_5m.set_agent_url(req.agent_url)
    
    settings.RISK_PERCENT = req.risk
    settings.AGENT_URL = req.agent_url # Update pydantic model too

    # 2. Persist to .env File
    update_env_file("AGENT_URL", req.agent_url)
    # Persisting RISK is optional but good practice if needed, focusing on IP per request
    # update_env_file("RISK_PERCENT", str(req.risk))

    engine_btc_breakout_5m.log(f"Settings updated: Agent={req.agent_url}")
    return {"status": "updated", "persisted": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


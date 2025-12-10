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


from backend.strategy_engine import StrategyEngine
from backend.config import settings


from strategy.TMA.tma_strategy import TMAStrategy
from strategy.DEMASuTBB.demasutbb_strategy import DEMASuTBBStrategy
import os
from datetime import datetime



# Instantiate Dual Engines
engine_swing = StrategyEngine(name="SWING", mode="4H1H", log_file="logs/4H1H/trading.log")
engine_scalp = StrategyEngine(name="SCALP", mode="15m1m", log_file="logs/15m1m/trading.log")
engine_tma = StrategyEngine(name="TMA", mode="4H15m", log_file="logs/TMA/trading.log", strategy_class=TMAStrategy)

# GOLD Strategies
engine_gold_45m = StrategyEngine(name="GOLD_45m", mode="GOLD_45m", log_file="logs/GOLD/45m.log", strategy_class=DEMASuTBBStrategy, symbols=["GOLD"])
engine_gold_15m = StrategyEngine(name="GOLD_15m", mode="GOLD_15m", log_file="logs/GOLD/15m.log", strategy_class=DEMASuTBBStrategy, symbols=["GOLD"])
engine_gold_5m = StrategyEngine(name="GOLD_5m", mode="GOLD_5m", log_file="logs/GOLD/5m.log", strategy_class=DEMASuTBBStrategy, symbols=["GOLD"])

# Global loop controller
loop_active = True

async def monitor_account():
    '''Independent loop to fetch account info regardless of strategy status'''
    while loop_active:
        async with aiohttp.ClientSession() as session:
             # Use Swing Engine logic to update its account info, which is shared
             # Or better, just call engine_swing.update_account_info(session)
             # We rely on engine_swing to hold the "Master" account info.
             await engine_swing.update_account_info(session)
        await asyncio.sleep(5)

async def bot_background_loop():
    while loop_active:
        tasks = []
        if engine_swing.active:
            tasks.append(engine_swing.run_loop())
        if engine_scalp.active:
            tasks.append(engine_scalp.run_loop())
        if engine_tma.active:
            tasks.append(engine_tma.run_loop())
        if engine_gold_45m.active:
            tasks.append(engine_gold_45m.run_loop())
        if engine_gold_15m.active:
            tasks.append(engine_gold_15m.run_loop())
        if engine_gold_5m.active:
            tasks.append(engine_gold_5m.run_loop())
            
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
    global loop_active
    loop_active = False


app = FastAPI(lifespan=lifespan)

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

# Enable CORS for Django Frontend (Port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

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
    if req.strategy.lower() == "swing": target_engine = engine_swing
    elif req.strategy.lower() == "scalp": target_engine = engine_scalp
    elif req.strategy.lower() == "tma": target_engine = engine_tma
    elif req.strategy.lower() == "gold_45m": target_engine = engine_gold_45m
    elif req.strategy.lower() == "gold_15m": target_engine = engine_gold_15m
    elif req.strategy.lower() == "gold_5m": target_engine = engine_gold_5m
    
    if target_engine:
        async with aiohttp.ClientSession() as session:
            # 1. Fetch Real Price
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
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/mean_reversion")
def read_mean_reversion(request: Request):
    return templates.TemplateResponse("mean_reversion.html", {"request": request})

@app.get("/tma")
def read_tma(request: Request):
    return templates.TemplateResponse("tma.html", {"request": request})

@app.get("/api/status")
def get_status():
    return {
        "swing": {
            "active": engine_swing.active,
            "status": engine_swing.status,
            "market_data": engine_swing.market_data,
            "logs": engine_swing.logs[:20]
        },
        "scalp": {
            "active": engine_scalp.active,
            "status": engine_scalp.status,
            "market_data": engine_scalp.market_data,
            "logs": engine_scalp.logs[:20]
        },
        "tma": {
            "active": engine_tma.active,
            "status": engine_tma.status,
            "market_data": engine_tma.market_data,
            "logs": engine_tma.logs[:20]
        },
        "gold": {
            "45m": {"active": engine_gold_45m.active, "status": engine_gold_45m.status, "data": engine_gold_45m.market_data, "logs": engine_gold_45m.logs[:5]},
            "15m": {"active": engine_gold_15m.active, "status": engine_gold_15m.status, "data": engine_gold_15m.market_data, "logs": engine_gold_15m.logs[:5]},
            "5m": {"active": engine_gold_5m.active, "status": engine_gold_5m.status, "data": engine_gold_5m.market_data, "logs": engine_gold_5m.logs[:5]},
        },
        "account": engine_swing.account_info, # Sharing account info
        "config": {
            "agent_url": engine_swing.agent_url,
            "risk": settings.RISK_PERCENT,
            "telegram_connected": bool(engine_swing.notifier and engine_swing.notifier.chat_id)
        }
    }

@app.post("/api/control")
async def control_bot(req: ControlRequest):
    if req.action == "start":
        if req.target in ["swing", "all"]:
            engine_swing.start()
        if req.target in ["scalp", "all"]:
            engine_scalp.start()
        if req.target in ["tma", "all"]:
            engine_tma.start()
        if req.target in ["gold", "all"]:
            engine_gold_45m.start()
            engine_gold_15m.start()
            engine_gold_5m.start()
            
    elif req.action == "stop":
        if req.target in ["swing", "all"]:
            engine_swing.stop()
        if req.target in ["scalp", "all"]:
            engine_scalp.stop()
        if req.target in ["tma", "all"]:
            engine_tma.stop()
        if req.target in ["gold", "all"]:
            engine_gold_45m.stop()
            engine_gold_15m.stop()
            engine_gold_5m.stop()
            
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

@app.post("/api/settings")
def update_settings(req: SettingsRequest):
    # 1. Update In-Memory Config (Immediate Effect)
    engine_swing.set_agent_url(req.agent_url)
    engine_scalp.set_agent_url(req.agent_url)
    engine_tma.set_agent_url(req.agent_url) 
    engine_gold_45m.set_agent_url(req.agent_url)
    engine_gold_15m.set_agent_url(req.agent_url)
    engine_gold_5m.set_agent_url(req.agent_url)
    settings.RISK_PERCENT = req.risk
    settings.AGENT_URL = req.agent_url # Update pydantic model too

    # 2. Persist to .env File
    update_env_file("AGENT_URL", req.agent_url)
    # Persisting RISK is optional but good practice if needed, focusing on IP per request
    # update_env_file("RISK_PERCENT", str(req.risk))

    engine_swing.log(f"Settings updated: Agent={req.agent_url}")
    return {"status": "updated", "persisted": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


import logging
import asyncio
import aiohttp
import pandas as pd
from datetime import datetime
from strategy.mean_reversion import MeanReversionRSI
from backend.config import settings
from backend.risk_manager import RiskManager
from backend.database import db
from backend.telegram_bot import TelegramNotifier

import logging
from logging.handlers import RotatingFileHandler
import os

import logging
from logging.handlers import RotatingFileHandler
import os

# Base logger config (optional if we want a root logger, but we'll use instance loggers)
# logging.basicConfig(level=logging.INFO)

class StrategyEngine:
    def __init__(self, name, mode, log_file, strategy_class=MeanReversionRSI):
        self.name = name
        self.active_mode = mode # Fixed mode for this instance
        self.log_file = log_file
        
        # Setup Instance Logger
        self.logger = logging.getLogger(f"StrategyEngine_{name}")
        self.logger.setLevel(logging.INFO)
        # Clear existing handlers to avoid duplicates on restart
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
            
        handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
        formatter = logging.Formatter(f'%(asctime)s - [{name}] - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Console Handler (optional, maybe noisy for two bots)
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        self.logger.addHandler(console)

        self.strategy = strategy_class()
        self.active = False
        self.agent_url = settings.AGENT_URL
        self.symbols = settings.SYMBOLS
        self.status = {s: "Idle" for s in self.symbols}
        self.market_data = {s: {} for s in self.symbols}
        self.account_info = {"balance": 0.0, "equity": 0.0}
        self.logs = []
        self.risk_manager = RiskManager()
        
        # Init DB
        db.connect()
        
        # Init Telegram
        self.notifier = TelegramNotifier(settings.TELEGRAM_TOKEN, settings.TELEGRAM_CHAT_ID)
        self.connected = False 
        self.notification_pending = False
        
        # State Tracking to prevent spam
        self.last_trade = {s: None for s in self.symbols} 
        self.active_positions = {s: False for s in self.symbols} 

    def log(self, message):
        self.logger.info(message) # Write to file/console
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs.insert(0, entry)
        if len(self.logs) > 100:
            self.logs.pop()

    def set_agent_url(self, url):
        self.agent_url = url

    def start(self): 
        # Mode is already set in __init__
        self.active = True
        self.log(f"Bot Started ({self.active_mode})")
        self.notification_pending = True
        self.status = {s: "Scanning..." for s in self.symbols} 

    def stop(self):
        self.active = False
        self.log("Bot stopped.")
        # We can't await here easily as this is synchronous, but we can try to fire-and-forget or just log
        # For simplicity in this architecture, we rely on the loop or just skip async stop msg for now,
        # OR we can make this async if main.py is updated. 
        # But easier: just let it be silent on stop or use create_task if loop running.
        for s in self.symbols:
            self.status[s] = "Stopped"

    async def fetch_candles(self, session, symbol, timeframe, n=200):
        try:
            url = f"{self.agent_url}/data/{symbol}/{timeframe}?n={n}"
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    df = pd.DataFrame(data)
                    return df
                else:
                    # self.log(f"Error fetching {symbol} {timeframe}: {resp.status}")
                    return None
        except Exception as e:
            # self.log(f"Connection error fetching {symbol}: {str(e)}")
            return None

    async def execute_trade(self, session, symbol, signal, entry, sl, tp, order_type="limit"):
        # 1. Get Account Balance
        balance = 0.0
        try:
            async with session.get(f"{self.agent_url}/account", timeout=5) as resp:
                if resp.status == 200:
                    info = await resp.json()
                    balance = info.get('balance', 0.0)
        except:
            self.log(f"Could not fetch balance. Using default 0.")

        # 2. Calculate Lot Size
        qty = self.risk_manager.calculate_lot_size(balance, settings.RISK_PERCENT, entry, sl)
        
        if qty <= 0:
            self.log(f"calculated qty is 0. Aborting trade for {symbol}")
            return

        # 3. Send Order
        precision = 5 if "DOGE" in symbol else 2
        
        payload = {
            "symbol": symbol,
            "action": "buy" if signal == "long" else "sell",
            "volume": float(qty),
            "price": round(float(entry), precision),
            "sl": round(float(sl), precision),
            "tp": round(float(tp), precision),
            "order_type": order_type
        }
        
        self.log(f"Sending Order {symbol} ({order_type}): Price={payload['price']}, SL={payload['sl']}, TP={payload['tp']}")

        try:
            async with session.post(f"{self.agent_url}/trade", json=payload, timeout=10) as resp:
                if resp.status == 200:
                    msg = f"Order Sent! {symbol} {signal} @ {entry} Qty: {qty}"
                    self.log(msg)
                    # DB Log
                    try: 
                        db.log_trade(symbol, self.name, signal, entry, qty, "ORDER_SENT")
                    except: pass
                    # Telegram Notify
                    await self.notifier.send_message(f"🚀 [{self.name}] {msg}")
                else:
                    err = await resp.text()
                    msg = f"Order failed {symbol}: {err}"
                    self.log(msg)
                    await self.notifier.send_message(f"⚠️ {msg}")
        except Exception as e:
            msg = f"Order connection error {symbol}: {str(e)}"
            self.log(msg)
            await self.notifier.send_message(f"🚨 {msg}")

    async def update_account_info(self, session):
        try:
            async with session.get(f"{self.agent_url}/account", timeout=5) as resp:
                if resp.status == 200:
                    info = await resp.json()
                    self.account_info = {
                        "balance": info.get('balance', 0.0),
                        "equity": info.get('equity', 0.0),
                        "margin": info.get('margin', 0.0)
                    }
                    
                    # Connection Restored Logic
                    if not self.connected:
                        self.connected = True
                        await self.notifier.send_message("📶 Connection to Agent Restored")
                        self.log("Connection Restored")
                        
                else:
                    raise Exception(f"Status {resp.status}")
                    
        except Exception as e:
            # Connection Lost Logic
            if self.connected:
                self.connected = False
                await self.notifier.send_message("❌ Connection Lost to Windows Agent")
                self.log("Connection Lost")

    async def run_loop(self):
        """Main loop called periodically from main.py or background task"""
        if not self.active:
            return

        # Send Start Notification if pending
        if self.notification_pending:
            await self.notifier.send_message(f"🟢 Bot Started - Mode: {self.active_mode}")
            self.notification_pending = False

        async with aiohttp.ClientSession() as session:
            # Update Account Info (Acts as Heartbeat)
            await self.update_account_info(session)
            
            # If not connected, we skip trading logic but keep retrying account info next loop
            if not self.connected:
                for symbol in self.symbols:
                    self.status[symbol] = "Connection Lost"
                return

            # Determine Timeframes based on Mode
            mode_config = settings.MODES.get(self.active_mode, settings.MODES["4H1H"])
            tf_current = mode_config["current"]
            tf_higher = mode_config["higher"]

            for symbol in self.symbols:
                if not self.active: break
                
                self.status[symbol] = f"Scanning ({self.active_mode})..."
                
                # Fetch Data
                df_curr = await self.fetch_candles(session, symbol, tf_current)
                df_high = await self.fetch_candles(session, symbol, tf_higher)
                
                if df_curr is not None and df_high is not None:
                    # Log data size
                    # self.log(f"{symbol} Data: Curr={len(df_curr)}, High={len(df_high)}")
                    
                    # Calculate Indicators
                    try:
                        indicators = self.strategy.calculate_indicators(df_curr, df_high)
                        if indicators:
                            # Update UI Data
                            # Update UI Data
                            self.market_data[symbol] = indicators
                            
                            
                            signal = self.strategy.get_signal(indicators)
                            
                            if signal:
                                # CHECK: Prevent duplicate orders
                                if self.active_positions.get(symbol, False):
                                    # Already in trade, skip
                                    self.status[symbol] = f"In Position ({signal})"
                                else:
                                    msg = f"Signal found for {symbol}: {signal}"
                                    self.log(msg)
                                    entry, sl, tp = self.strategy.get_entry_params(signal, indicators)
                                    await self.execute_trade(session, symbol, signal, entry, sl, tp)
                                    
                                    # Mark as active to prevent loop
                                    self.active_positions[symbol] = True
                                    self.status[symbol] = f"Signal: {signal}"
                            else:
                                self.status[symbol] = "Scanning"
                                # Reset position flag if no signal (Or better, check actual position from agent)
                                # For now, we reset if signal is gone, but ideally we sync with Agent positions.
                                # Simple fix for loop: Only reset if we confirm NO position from Agent.
                                # But for this step, just relying on signal is risky. 
                                # Better approach: Reset flag after some time or check agent.
                                # Let's assume for now we want to take the trade once per signal occurence.
                                # But signal persists for entire candle (1H). 
                                pass
                        else:
                            self.status[symbol] = "Insufficient Data"
                            self.log(f"{symbol}: Insufficient Data (Candles: {len(df_curr)}/{len(df_high)})")
                    except Exception as e:
                        self.log(f"Error analyzing {symbol}: {e}")
                        self.status[symbol] = "Error"
                        import traceback
                        traceback.print_exc()
                else:
                    self.status[symbol] = "Connection Error"
                    # self.log(f"{symbol}: Fetch failed")
                
                # Short sleep between symbols not to flood
                await asyncio.sleep(1)

# Engine is now instantiated in main.py

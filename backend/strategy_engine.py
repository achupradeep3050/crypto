import logging
import asyncio
import aiohttp
import pandas as pd
from datetime import datetime
# from strategy.mean_reversion import MeanReversionRSI - REMOVED
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
    def __init__(self, name, mode, log_file, strategy_class=None, symbols=None):
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
        
        # Use provided symbols or default from settings
        self.symbols = symbols if symbols is not None else settings.SYMBOLS
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
                    # Realtime DB Saving/Caching
                    try:
                        db.save_candles(symbol, timeframe, data)
                    except Exception as db_e:
                        self.log(f"DB Cache Warning: {db_e}")
                        
                    df = pd.DataFrame(data)
                    return df
                else:
                    # self.log(f"Error fetching {symbol} {timeframe}: {resp.status}")
                    return None
        except Exception as e:
            # self.log(f"Connection error fetching {symbol}: {str(e)}")
            return None

    async def execute_trade(self, session, symbol, signal, entry, sl, tp, order_type="market"):
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
        # Check if strategy has custom sizing (e.g. BitcoinBreakout with compounding)
        if hasattr(self.strategy, 'get_position_size'):
            qty = self.strategy.get_position_size(balance)
        else:
            # Default to fixed risk %
            qty = self.risk_manager.calculate_lot_size(balance, settings.RISK_PERCENT, entry, sl)
        
        # Safety for negative/zero balance
        if qty <= 0:
            qty = 0.01 # Minimum safety or abort? Abort logic below handles it.
        
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
            "deviation": 20,
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
                
                # Fetch Higher TF only if configured
                df_high = None
                if tf_higher:
                    df_high = await self.fetch_candles(session, symbol, tf_higher)
                
                # Logic: Current TF is mandatory. Higher TF is mandatory ONLY if it was requested.
                # If tf_higher is None, df_high stays None, and that is valid.
                valid_data = (df_curr is not None) and (not tf_higher or df_high is not None)
                
                if valid_data:
                    # Log data size (Optional debugging)
                    # self.log(f"{symbol} Data: Curr={len(df_curr)} High={'None' if df_high is None else len(df_high)}")
                    
                    # Calculate Indicators
                    try:
                        indicators = self.strategy.calculate_indicators(df_curr, df_high)
                        if indicators is not None:
                            # Update UI Data
                            if not indicators.empty:
                                try:
                                    last_row = indicators.iloc[-1].copy()
                                    # Fill NaNs with None for JSON safety
                                    last_row = last_row.where(pd.notnull(last_row), None)
                                    # Convert timestamps
                                    if 'time' in last_row: last_row['time'] = str(last_row['time'])
                                    self.market_data[symbol] = last_row.to_dict()
                                except Exception as e:
                                    self.log(f"[ERROR] Serialization Error {symbol}: {e}")
                                    self.market_data[symbol] = {}
                            
                            signal = self.strategy.get_signal(indicators)
                            
                            # Detailed Tester Logging
                            if not indicators.empty:
                                close_p = indicators.iloc[-1]['close']
                                # Try to log key indicators if they exist
                                adx_str = f"ADX={indicators.iloc[-1].get('adx', 'N/A'):.1f}" if 'adx' in indicators.columns else ""
                                rsi_str = f"RSI={indicators.iloc[-1].get('rsi', 'N/A'):.1f}" if 'rsi' in indicators.columns else ""
                                self.log(f"[SCAN] {symbol} Price={close_p} {adx_str} {rsi_str} Signal={signal}")

                            # --- TRADE MANAGER (Exits) ---
                            current_position = self.active_positions.get(symbol)
                            if current_position:
                                # Check for Exit Signal
                                should_exit = False
                                try:
                                    should_exit = self.strategy.get_exit_signal(indicators, current_position)
                                except: pass # Strategy might not support exits
                                
                                if should_exit:
                                    self.log(f"[EXIT] Exit Signal for {symbol} ({current_position})")
                                    # Close Position: Send Opposite Order
                                    close_action = "short" if current_position == "long" else "long"
                                    # Amount? We assume full close. Using same qty logic or just flat close.
                                    # For simplicity/MVP: Send a Market Close. 
                                    # Agent API is simple buy/sell. We send opposite.
                                    # We don't track exact Qty here perfectly yet, but assumes 1 trade per symbol.
                                    
                                    # Get current price for logging
                                    exit_price = indicators.iloc[-1]['close'] if not indicators.empty else 0
                                    
                                    # Execute Close
                                    # We use 0 as Entry/SL/TP for close order basically, relying on Market execution
                                    await self.execute_trade(session, symbol, close_action, exit_price, 0, 0, order_type="market")
                                    
                                    self.active_positions[symbol] = False
                                    self.status[symbol] = "Closed Trade"
                                    self.log(f"[TRADE] Position Closed {symbol}")
                                else:
                                    self.status[symbol] = f"In Trade ({current_position})"
                            
                            # --- ENTRY MANAGER ---
                            elif signal:
                                msg = f"[SIGNAL] Signal found for {symbol}: {signal}"
                                self.log(msg)
                                entry, sl, tp = self.strategy.get_entry_params(signal, indicators)
                                await self.execute_trade(session, symbol, signal, entry, sl, tp)
                                
                                # Mark as active with type
                                self.active_positions[symbol] = signal
                                self.status[symbol] = f"Entered: {signal}"
                            else:
                                self.status[symbol] = "Scanning"
                                # pass
                        else:
                            self.status[symbol] = "Insufficient Data"
                            self.log(f"[WARN] {symbol}: Insufficient Data (Candles: {len(df_curr)}/{len(df_high) if df_high is not None else 0})")
                    except Exception as e:
                        self.log(f"[ERROR] analyzing {symbol}: {e}")
                        self.status[symbol] = "Error"
                        import traceback
                        traceback.print_exc()
                else:
                    self.status[symbol] = "Connection Error"
                    # Safe logging for None types
                    curr_len = len(df_curr) if df_curr is not None else 0
                    high_len = len(df_high) if df_high is not None else 0
                    self.log(f"[WARN] {symbol}: Fetch Failed or Insufficient Data. Candles: {curr_len}/{high_len}")
                
                # Short sleep between symbols not to flood
                await asyncio.sleep(1)

# Engine is now instantiated in main.py

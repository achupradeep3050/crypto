
import asyncio
import pandas as pd
import pandas_ta as ta
import sys
import os
import numpy as np

sys.path.append(os.getcwd())
from backend.backtest_engine import BacktestEngine

class UniversalStrategy:
    def __init__(self, params):
        self.params = params
        
    def calculate_indicators(self, df):
        # Common Indicators
        if self.params.get('use_ema_trend', True):
            df['ema_trend'] = ta.ema(df['close'], length=self.params['trend_ema'])
            
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
        
        # Strategy Specific
        stype = self.params['type']
        
        if stype == 'rsi_pullback':
            df['rsi'] = ta.rsi(df['close'], length=14)
            
        elif stype == 'bb_reversion':
            bb = ta.bbands(df['close'], length=20, std=2)
            df['bb_lower'] = bb.iloc[:, 0]
            df['bb_upper'] = bb.iloc[:, 2]
            df['rsi'] = ta.rsi(df['close'], length=14) # Filter
            
        elif stype == 'stoch_rsi':
            stoch = ta.stochrsi(df['close'], length=14, rsi_length=14, k=3, d=3)
            df['stoch_k'] = stoch.iloc[:, 0]
            df['stoch_d'] = stoch.iloc[:, 1]
            
        elif stype == 'breakout':
            # Donchian Channel / High-Low Breakout
            period = self.params.get('breakout_period', 20)
            df['high_n'] = df['high'].rolling(period).max().shift(1) # Previous N High
            df['low_n'] = df['low'].rolling(period).min().shift(1)   # Previous N Low
            
        return df

    def get_signal(self, window):
        curr = window.iloc[-2] # Closed candle
        stype = self.params['type']
        
        # Trend Check
        trend_up = True
        trend_down = True
        if self.params.get('use_ema_trend', True):
            trend_up = curr['close'] > curr['ema_trend']
            trend_down = curr['close'] < curr['ema_trend']
            
        # ADX Check (if required by params)
        strong_trend = True
        if 'adx_min' in self.params:
             strong_trend = curr['adx'] > self.params['adx_min']
        
        if stype == 'rsi_pullback':
            rsi = curr['rsi']
            if trend_up and strong_trend and rsi < self.params['rsi_oversold']: return 'long'
            if trend_down and strong_trend and rsi > (100 - self.params['rsi_oversold']): return 'short'
            
        elif stype == 'bb_reversion':
            # Relaxed partial candle close check? No, sticking to strict
            if trend_up and curr['low'] <= curr['bb_lower'] and curr['rsi'] < 50: return 'long' # Widened to 50
            if trend_down and curr['high'] >= curr['bb_upper'] and curr['rsi'] > 50: return 'short'
            
        elif stype == 'stoch_rsi':
            k = curr['stoch_k']
            d = curr['stoch_d']
            prev = window.iloc[-3]
            
            # Cross Up in Oversold
            cross_up = prev['stoch_k'] < prev['stoch_d'] and k > d
            oversold = k < 30 and d < 30 # Relaxed from 20
            
            if trend_up and cross_up and oversold: return 'long'
            
            # Cross Down in Overbought
            cross_down = prev['stoch_k'] > prev['stoch_d'] and k < d
            overbought = k > 70 and d > 70 # Relaxed from 80
            
            if trend_down and cross_down and overbought: return 'short'
            
        elif stype == 'breakout':
            # Breakout Long
            if curr['close'] > curr['high_n'] and strong_trend: return 'long'
            # Breakout Short
            if curr['close'] < curr['low_n'] and strong_trend: return 'short'
            
        return None

class ResearchRunner(BacktestEngine):
    def run_simulation(self, strategy_params, df):
        if df.empty: return {'wr': 0, 'roi': 0, 'trades': 0}
        
        balance = 1000
        trades = []
        position = None
        
        strat = UniversalStrategy(strategy_params)
        df = strat.calculate_indicators(df.copy())
        
        # Determine strictness of RR
        rr = strategy_params.get('rr', 2.0)
        
        for i in range(200, len(df)):
            curr = df.iloc[i]
            window = df.iloc[:i+1]
            
            if position:
                if position['type'] == 'long':
                    if curr['low'] <= position['sl']:
                        pnl = (position['sl'] - position['entry']) * position['size']
                        balance += pnl
                        trades.append({'pnl': pnl, 'res': 'loss'})
                        position = None
                    elif curr['high'] >= position['tp']:
                        pnl = (position['tp'] - position['entry']) * position['size']
                        balance += pnl
                        trades.append({'pnl': pnl, 'res': 'win'})
                        position = None
                elif position['type'] == 'short':
                    if curr['high'] >= position['sl']:
                        pnl = (position['entry'] - position['sl']) * position['size']
                        balance += pnl
                        trades.append({'pnl': pnl, 'res': 'loss'})
                        position = None
                    elif curr['low'] <= position['tp']:
                         pnl = (position['entry'] - position['tp']) * position['size']
                         balance += pnl
                         trades.append({'pnl': pnl, 'res': 'win'})
                         position = None
            
            if not position:
                sig = strat.get_signal(window)
                if sig:
                    atr = curr['atr']
                    sl_dist = atr * strategy_params['sl_atr']
                    
                    if sig == 'long':
                        entry = curr['close']
                        sl = entry - sl_dist
                        tp = entry + (sl_dist * rr)
                        risk = entry - sl
                        if risk == 0: continue
                        size = (balance * 0.05) / risk
                        position = {'type': 'long', 'entry': entry, 'sl': sl, 'tp': tp, 'size': size}
                    elif sig == 'short':
                        entry = curr['close']
                        sl = entry + sl_dist
                        tp = entry - (sl_dist * rr)
                        risk = sl - entry
                        if risk == 0: continue
                        size = (balance * 0.05) / risk
                        position = {'type': 'short', 'entry': entry, 'sl': sl, 'tp': tp, 'size': size}

        wins = len([t for t in trades if t['pnl'] > 0])
        total = len(trades)
        wr = (wins / total * 100) if total > 0 else 0
        roi = ((balance - 1000) / 1000) * 100
        
        return {'wr': wr, 'roi': roi, 'trades': total}

async def main():
    engine = ResearchRunner("http://localhost:8001")
    
    print("Fetching 200 Days of Data...")
    now = pd.Timestamp.now()
    start_ts = int((now - pd.Timedelta(days=200)).timestamp())
    end_ts = int(now.timestamp())
    
    # Using 15m for speed/relevance for now? User said "any timeframe".
    # 5m data for 200 days is huge (~57k candles). Might fit.
    # Let's try 5m.
    df_200 = await engine.get_data("BITCOIN", "5m", start_ts, end_ts)
    
    if df_200.empty:
        print("Failed to fetch data.")
        return
        
    print(f"Loaded {len(df_200)} candles.")
    
    # Create Subsets
    # Assuming index is standard range, but we need time-based slicing
    # BacktestEngine returns df with 'time' column (unix).
    
    df_200['datetime'] = pd.to_datetime(df_200['time'], unit='s')
    df_200.set_index('datetime', inplace=True, drop=False)
    
    limit_100 = now - pd.Timedelta(days=100)
    limit_30 = now - pd.Timedelta(days=30)
    
    df_100 = df_200[df_200.index >= limit_100]
    df_30 = df_200[df_200.index >= limit_30]
    
    print(f"Subsets: 200d={len(df_200)}, 100d={len(df_100)}, 30d={len(df_30)}")
    
    # Strategy Configs
    configs = []
    
    # RSI Pullback Variations (Widened)
    for ema in [100, 200]:
        for rsi_os in [30, 35, 40, 45]:
            configs.append({'type': 'rsi_pullback', 'trend_ema': ema, 'rsi_oversold': rsi_os, 'rsi_overbought': 100-rsi_os, 'adx_min': 15, 'sl_atr': 2.0, 'rr': 2.0, 'use_ema_trend': True})

    # BB Reversion Variations (Relaxed ADX)
    for ema in [100, 200]:
        configs.append({'type': 'bb_reversion', 'trend_ema': ema, 'adx_min': 0, 'sl_atr': 2.0, 'rr': 2.0, 'use_ema_trend': True}) # No ADX
        
    # Stoch RSI
    for ema in [100, 200]:
        configs.append({'type': 'stoch_rsi', 'trend_ema': ema, 'adx_min': 15, 'sl_atr': 1.5, 'rr': 2.0, 'use_ema_trend': True})
        
    # Breakout Variations
    for ema in [50, 100]:
        for period in [20, 50]:
            configs.append({'type': 'breakout', 'trend_ema': ema, 'breakout_period': period, 'adx_min': 20, 'sl_atr': 1.5, 'rr': 2.0, 'use_ema_trend': True})
            configs.append({'type': 'breakout', 'trend_ema': ema, 'breakout_period': period, 'adx_min': 25, 'sl_atr': 1.5, 'rr': 2.0, 'use_ema_trend': True})

    # Run Optimization
    
    print("\n--- Phase 1: Screening on 30 Days (Target: >5 trades, >35% WR) ---")
    
    shortlist = []
    for i, cfg in enumerate(configs):
        res = engine.run_simulation(cfg, df_30)
        # Criteria: Trades > 5, WR > 35% (Minimal baseline)
        if res['trades'] >= 5 and res['wr'] > 35:
            cfg.update(res) # Store 30d results
            shortlist.append(cfg)
            print(f"[{i}] Pass: {cfg['type']} | WR: {res['wr']:.1f}% | Trades: {res['trades']} | ROI: {res['roi']:.1f}%")
            
    print(f"\nShortlisted {len(shortlist)} configs. Running full validation (100d, 200d)...")
    
    final_results = []
    for cfg in shortlist:
        # Test 100d
        res_100 = engine.run_simulation(cfg, df_100)
        # Test 200d
        res_200 = engine.run_simulation(cfg, df_200)
        
        # Aggregated Score?
        # User wants > 85% WR. 
        # If we can't find 85%, show best.
        
        # Calculate consistency
        avg_wr = (cfg['wr'] + res_100['wr'] + res_200['wr']) / 3
        
        combined = {
            'params': {k:v for k,v in cfg.items() if k not in ['wr', 'roi', 'trades']}, # Clean params
            '30d': {'wr': cfg['wr'], 'roi': cfg['roi'], 'trades': cfg['trades']},
            '100d': {'wr': res_100['wr'], 'roi': res_100['roi'], 'trades': res_100['trades']},
            '200d': {'wr': res_200['wr'], 'roi': res_200['roi'], 'trades': res_200['trades']},
            'avg_wr': avg_wr
        }
        final_results.append(combined)

    # Sort by Avg WR
    final_results.sort(key=lambda x: x['avg_wr'], reverse=True)
    
    print("\n--- TOP RANKED STRATEGIES ---")
    for r in final_results[:3]:
        print(f"\nStrategy: {r['params']['type']} (EMA calculated)")
        print(f"Params: {r['params']}")
        print(f"30d : WR={r['30d']['wr']:.1f}% Trades={r['30d']['trades']} ROI={r['30d']['roi']:.1f}%")
        print(f"100d: WR={r['100d']['wr']:.1f}% Trades={r['100d']['trades']} ROI={r['100d']['roi']:.1f}%")
        print(f"200d: WR={r['200d']['wr']:.1f}% Trades={r['200d']['trades']} ROI={r['200d']['roi']:.1f}%")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

import asyncio
import pandas as pd
import datetime
from backend.database import db
from backend.backtest_engine import BacktestEngine
from strategy.BitcoinBreakout.bitcoin_breakout import BitcoinBreakout
from tabulate import tabulate

# Config
CAPITAL = 100
SYMBOL = "BITCOIN"
TIMEFRAME = "5m"
DAYS_LIST = [30, 100, 300]
REPORT_FILE = "Bitcoin_Breakout_Report.md"

async def run_report():
    print(f"Generating Report for {SYMBOL} {TIMEFRAME} with ${CAPITAL} Capital...")
    
    engine = BacktestEngine(agent_url="http://192.168.122.121:8001")
    
    report_content = f"# Bitcoin Breakout Strategy Backtest Report\n\n"
    report_content += f"**Strategy**: Bitcoin Breakout (5m)\n"
    report_content += f"**Initial Capital**: ${CAPITAL}\n"
    report_content += f"**Timestamp**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    summary_data = []

    for days in DAYS_LIST:
        print(f"  Running {days}-Day Backtest...")
        
        end_ts = int(datetime.datetime.now().timestamp())
        start_ts = end_ts - (days * 24 * 60 * 60)
        
        # 1. Fetch Data
        df = await engine.get_data(SYMBOL, TIMEFRAME, start_ts, end_ts)
        
        if df.empty:
            print(f"    No data for {days} days.")
            continue
            
        # 2. Run Backtest
        result = engine.run(BitcoinBreakout, df, start_balance=CAPITAL)
        
        # 3. Process Results
        final_bal = result['final_balance']
        roi = ((final_bal - CAPITAL) / CAPITAL) * 100
        win_rate = float(result['win_rate']) * 100
        total_trades = result['total_trades']
        wl_ratio = f"{win_rate:.1f}%"
        
        summary_data.append([
            f"{days} Days", 
            f"${final_bal:.2f}", 
            f"{roi:.2f}%", 
            total_trades, 
            wl_ratio
        ])
        
        # 4. Append Trade List to Report
        report_content += f"## {days}-Day Performance\n"
        report_content += f"- **Final Balance**: ${final_bal:.2f}\n"
        report_content += f"- **ROI**: {roi:.2f}%\n"
        report_content += f"- **Total Trades**: {total_trades}\n"
        report_content += f"- **Win Rate**: {wl_ratio}\n\n"
        
        report_content += "### Trade History\n"
        if result['trades']:
            # Create Table from trades
            trade_rows = []
            for t in result['trades'][::-1]: # Reverse order
                dt = datetime.datetime.fromtimestamp(t['entry_time']).strftime('%Y-%m-%d %H:%M')
                pnl_str = f"+${t['pnl']:.2f}" if t['pnl'] >= 0 else f"-${abs(t['pnl']):.2f}"
                size = f"{t['size']:.2f}"
                trade_rows.append([
                    dt, t['type'].upper(), size, f"${t['entry']:.2f}", f"${t['exit']:.2f}", pnl_str
                ])
            
            # Markdown Table
            report_content += "| Date | Type | Size | Entry | Exit | PnL |\n"
            report_content += "|---|---|---|---|---|---|\n"
            for row in trade_rows:
                report_content += f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} |\n"
        else:
            report_content += "No trades executed.\n"
        
        report_content += "\n---\n\n"

    # Add Summary Table at Top
    summary_table = tabulate(summary_data, headers=["Period", "Final Balance", "ROI", "Trades", "Win Rate"], tablefmt="github")
    
    final_report = f"# Executive Summary\n\n{summary_table}\n\n" + report_content
    
    # Save File
    with open(REPORT_FILE, "w") as f:
        f.write(final_report)
    
    print(f"Report saved to {REPORT_FILE}")

if __name__ == "__main__":
    asyncio.run(run_report())

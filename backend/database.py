import mariadb
import sys
from backend.config import settings
import logging

logger = logging.getLogger("Database")

class Database:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect(self):
        try:
            self.conn = mariadb.connect(
                user="bot_user",
                password="bot_pass",
                host="localhost",
                port=3306,
                database="algo_trading"
            )
            self.cursor = self.conn.cursor()
            self.init_table()
            self.init_candle_table()
            logger.info("Connected to MariaDB")
        except mariadb.Error as e:
            logger.error(f"Error connecting to MariaDB: {e}")

    def init_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS trades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20),
            strategy VARCHAR(20), /* Added strategy column */
            action VARCHAR(10),
            price DOUBLE,
            volume DOUBLE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            result VARCHAR(255)
        )
        """
        try:
            self.cursor.execute(query)
            # Add column if missing (for existing tables)
            try:
                self.cursor.execute("ALTER TABLE trades ADD COLUMN strategy VARCHAR(20) AFTER symbol")
            except: pass  # Ignore if exists
            
            self.conn.commit()
        except mariadb.Error as e:
            logger.error(f"Error creating table: {e}")

    def init_candle_table(self):
        """Creates table for caching OHLCV data for backtesting"""
        query = """
        CREATE TABLE IF NOT EXISTS candles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20),
            timeframe VARCHAR(10),
            timestamp BIGINT, /* Unix Timestamp */
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            UNIQUE KEY unique_candle (symbol, timeframe, timestamp)
        )
        """
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except mariadb.Error as e:
            logger.error(f"Error creating candles table: {e}")

    def log_trade(self, symbol, strategy, action, price, volume, result):
        if not self.conn: self.connect()
        if not self.cursor: return

        try:
            self.cursor.execute(
                "INSERT INTO trades (symbol, strategy, action, price, volume, result) VALUES (?, ?, ?, ?, ?, ?)",
                (symbol, strategy, action, price, volume, result)
            )
            self.conn.commit()
        except mariadb.Error as e:
            logger.error(f"Error inserting trade: {e}")

    def save_candles(self, symbol, timeframe, candles):
        """
        Bulk insert/ignore candles.
        candles: list of dicts {'time': int, 'open': float...}
        """
        if not self.conn: self.connect()
        if not self.cursor: return

        try:
            data = []
            for c in candles:
                data.append((symbol, timeframe, c['time'], c['open'], c['high'], c['low'], c['close'], c.get('tick_volume', 0)))
            
            self.cursor.executemany(
                "INSERT IGNORE INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                data
            )
            self.conn.commit()
            logger.info(f"Cached {len(data)} candles for {symbol} {timeframe}")
        except mariadb.Error as e:
            logger.error(f"Error saving candles: {e}")

    def get_candles(self, symbol, timeframe, start_ts, end_ts):
        """Retrieve cached candles"""
        if not self.conn: self.connect()
        if not self.cursor: return []
        
        try:
            self.cursor.execute(
                "SELECT timestamp, open, high, low, close, volume FROM candles WHERE symbol=? AND timeframe=? AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp ASC",
                (symbol, timeframe, int(start_ts), int(end_ts))
            )
            rows = self.cursor.fetchall()
            # Convert to list of dicts matching Agent format
            return [
                {'time': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'tick_volume': r[5]} 
                for r in rows
            ]
        except mariadb.Error as e:
            logger.error(f"Error getting candles: {e}")
            return []

db = Database()


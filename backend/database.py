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

    def log_trade(self, symbol, strategy, action, price, volume, result):
        if not self.conn:
            self.connect()
        
        try:
            self.cursor.execute(
                "INSERT INTO trades (symbol, strategy, action, price, volume, result) VALUES (?, ?, ?, ?, ?, ?)",
                (symbol, strategy, action, price, volume, result)
            )
            self.conn.commit()
        except mariadb.Error as e:
            logger.error(f"Error inserting trade: {e}")
            
db = Database()


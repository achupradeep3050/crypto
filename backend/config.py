from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Windows Agent Configuration
    AGENT_URL: str = "http://192.168.122.121:8001" # User provided IP
    
    # Trading Configuration
    SYMBOLS: list = ["BITCOIN", "ETHEREUM", "DOGECOIN"]
    
    # Timeframe Modes
    MODES: dict = {
        "4H1H": {"current": "1h", "higher": "4h"},
        "15m1m": {"current": "1m", "higher": "15m"},
        "4H15m": {"current": "15m", "higher": "4h"}
    }
    
    # Defaults (can be removed if unused, but keeping for safety)
    TIMEFRAME_CURRENT: str = "1h" 
    TIMEFRAME_HIGHER: str = "4h"
    # Telegram Configuration
    TELEGRAM_TOKEN: str = "8483431667:AAHHs1kv01GJ-5cJ7L9wee_UZNeCDavMzPI"
    TELEGRAM_CHAT_ID: str = "5998452008" # Retrieved automatically
    
    # Risk Management
    RISK_PERCENT: float = 5.0  # 5% risk per trade
    
    class Config:
        env_file = ".env"

settings = Settings()

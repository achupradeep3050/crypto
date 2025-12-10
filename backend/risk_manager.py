class RiskManager:
    @staticmethod
    def calculate_lot_size(balance: float, risk_percent: float, entry_price: float, stop_loss_price: float, symbol_info: dict = None):
        """
        Calculates position size based on risk percentage and stop loss distance.
        """
        if balance <= 0 or entry_price <= 0 or stop_loss_price <= 0:
            return 0.0
            
        risk_amount = balance * (risk_percent / 100.0)
        
        # Distance to stop loss per unit
        price_diff = abs(entry_price - stop_loss_price)
        
        if price_diff == 0:
            return 0.0
            
        # Simplified lot calculation (assuming direct correlation for crypto or std lots)
        # For FX 1 lot = 100,000 units. For Crypto on MT5, it varies (often 1 local unit).
        # We need tick value logic for precise calculation, but usually:
        # Lot Size = Risk Amount / (Stop Loss pips * Pip Value)
        # Here we do a generic raw unit calculation first.
        
        # Qty = Risk / abs(Entry - SL)
        raw_qty = risk_amount / price_diff
        
        # If symbol_info provided, adjust for volume step/min volume
        if symbol_info:
            vol_step = symbol_info.get('volume_step', 0.01)
            vol_min = symbol_info.get('volume_min', 0.01)
            vol_max = symbol_info.get('volume_max', 100.0)
            
            # Round to nearest step
            import math
            if vol_step > 0:
                raw_qty = math.floor(raw_qty / vol_step) * vol_step
                
            raw_qty = max(vol_min, min(raw_qty, vol_max))
            
        return round(raw_qty, 2)

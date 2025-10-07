"""
Mock Data Generator for Trinity Wealth Scanner
Creates realistic market data for testing the Trinity strategy without live API
"""

import random
import datetime as dt
from datetime import timedelta
import pandas as pd
from typing import List, Dict, Any
import uuid

# Mock market data
MOCK_UNDERLYINGS = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
MOCK_STRIKES = {
    "NIFTY": list(range(24000, 26000, 50)),
    "BANKNIFTY": list(range(50000, 54000, 100)), 
    "FINNIFTY": list(range(22000, 24000, 50))
}

MOCK_SPOT_PRICES = {
    "NIFTY": 25000,
    "BANKNIFTY": 52000,
    "FINNIFTY": 23000
}

def generate_mock_expiry_dates(days_ahead: int = 60) -> List[dt.date]:
    """Generate realistic expiry dates (Thursdays)"""
    expiries = []
    today = dt.date.today()
    
    for i in range(days_ahead):
        date = today + timedelta(days=i)
        if date.weekday() == 3:  # Thursday
            expiries.append(date)
        if len(expiries) >= 8:
            break
    
    return expiries

def generate_mock_options_data(underlying: str = "NIFTY") -> List[Dict]:
    """Generate mock NFO options data"""
    options = []
    expiries = generate_mock_expiry_dates()
    strikes = MOCK_STRIKES.get(underlying, MOCK_STRIKES["NIFTY"])
    spot_price = MOCK_SPOT_PRICES.get(underlying, 25000)
    
    # Generate ATM and nearby strikes
    atm_strikes = [s for s in strikes if abs(s - spot_price) <= 500]
    
    for expiry in expiries[:3]:  # First 3 expiries
        for strike in atm_strikes[:10]:  # First 10 ATM strikes
            for option_type in ["CE", "PE"]:
                symbol = f"{underlying}{expiry.strftime('%y%b%d').upper()}{strike}{option_type}"
                
                # Mock realistic option pricing
                if option_type == "CE":
                    if strike < spot_price:
                        ltp = max(1, spot_price - strike + random.uniform(-50, 50))
                    else:
                        ltp = max(1, random.uniform(1, 100))
                else:  # PE
                    if strike > spot_price:
                        ltp = max(1, strike - spot_price + random.uniform(-50, 50))
                    else:
                        ltp = max(1, random.uniform(1, 100))
                
                options.append({
                    "instrument_token": random.randint(100000, 999999),
                    "tradingsymbol": symbol,
                    "name": underlying,
                    "instrument_type": option_type,
                    "strike": strike,
                    "expiry": expiry,
                    "lot_size": 50 if underlying == "NIFTY" else 25,
                    "last_price": round(ltp, 2),
                    "volume": random.randint(1000, 50000),
                    "oi": random.randint(10000, 100000),
                    "prev_close": round(ltp * random.uniform(0.9, 1.1), 2)
                })
    
    return options

def generate_mock_historical_data(symbol: str, days: int = 5) -> List[Dict]:
    """Generate mock historical candle data with Trinity patterns"""
    candles = []
    base_price = random.uniform(50, 500)
    
    # Generate 5 days of 15-minute candles
    start_time = dt.datetime.now() - timedelta(days=days)
    
    for day in range(days):
        day_start = start_time + timedelta(days=day)
        day_start = day_start.replace(hour=9, minute=15, second=0, microsecond=0)
        
        # Market hours: 9:15 AM to 3:30 PM (6 hours 15 minutes = 25 candles)
        for candle in range(25):
            candle_time = day_start + timedelta(minutes=15 * candle)
            
            # Create realistic price movement with some Trinity patterns
            if candle == 0:
                open_price = base_price
            else:
                open_price = candles[-1]["close"]
            
            # Add some volatility and patterns
            if random.random() < 0.1:  # 10% chance of significant move
                price_change = random.uniform(-20, 20)
            else:
                price_change = random.uniform(-5, 5)
            
            close_price = max(1, open_price + price_change)
            high_price = max(open_price, close_price) + random.uniform(0, 3)
            low_price = min(open_price, close_price) - random.uniform(0, 3)
            
            candles.append({
                "date": candle_time,
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": random.randint(1000, 10000)
            })
            
            base_price = close_price
    
    return candles

def create_mock_trinity_signals(num_signals: int = 3) -> List[Dict]:
    """Create mock Trinity signals that would be generated today"""
    signals = []
    today = dt.datetime.now()
    
    for i in range(num_signals):
        underlying = random.choice(MOCK_UNDERLYINGS)
        strike = random.choice(MOCK_STRIKES[underlying][:10])  # First 10 strikes
        option_type = random.choice(["CE", "PE"])
        
        entry_price = round(random.uniform(50, 300), 2)
        sl_pct = 0.1  # 0.1% as default
        tp_pct = 0.1
        
        sl_price = round(entry_price * (1 - sl_pct/100), 2)
        tp_price = round(entry_price * (1 + tp_pct/100), 2)
        rr = round((tp_price - entry_price) / (entry_price - sl_price), 2)
        
        # Generate signal time (random time today during market hours)
        signal_time = today.replace(
            hour=random.randint(9, 15),
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        
        # Random outcome for demo
        outcome = random.choice(["WIN", "LOSS", "PENDING", "PENDING", "PENDING"])  # More pending
        
        signals.append({
            "id": str(uuid.uuid4()),
            "underlying": underlying,
            "contract": f"{underlying}{today.strftime('%y%b%d').upper()}{strike}{option_type}",
            "symbol": f"{underlying}{today.strftime('%y%b%d').upper()}{strike}{option_type}",
            "entry_price": entry_price,
            "sl": sl_price,
            "tp": tp_price,
            "rr": rr,
            "lot": 50 if underlying == "NIFTY" else 25,
            "outcome": outcome,
            "signal_time": signal_time,
            "entry_time": signal_time,
            "poi_time": signal_time,
            "_entry_dt": signal_time,
            "created_at": signal_time,
            "ltp": entry_price,
            "_risk": round(entry_price - sl_price, 2),
            "_reward": round(tp_price - entry_price, 2),
            
            # Trinity-specific fields
            "bos_index": random.randint(10, 20),
            "induc_index": random.randint(15, 25),
            "entry_index": random.randint(20, 30),
            "bos_time": signal_time - timedelta(minutes=random.randint(30, 120)),
            "induc_time": signal_time - timedelta(minutes=random.randint(15, 60)),
            "hit_time": signal_time + timedelta(minutes=random.randint(15, 180)) if outcome != "PENDING" else None,
            "exit_price": tp_price if outcome == "WIN" else sl_price if outcome == "LOSS" else None
        })
    
    return signals

def generate_mock_atm_options(underlying: str = "NIFTY") -> List[Dict]:
    """Generate mock ATM options for display"""
    spot_price = MOCK_SPOT_PRICES.get(underlying, 25000)
    strikes = MOCK_STRIKES.get(underlying, MOCK_STRIKES["NIFTY"])
    
    # Find ATM strikes
    atm_strikes = sorted([s for s in strikes if abs(s - spot_price) <= 200])[:5]
    
    options = []
    expiry = generate_mock_expiry_dates()[0]  # Nearest expiry
    
    for strike in atm_strikes:
        for option_type in ["CE", "PE"]:
            symbol = f"{underlying}{expiry.strftime('%y%b%d').upper()}{strike}{option_type}"
            
            # Mock pricing
            if option_type == "CE":
                ltp = max(1, spot_price - strike + random.uniform(-20, 20)) if strike < spot_price else random.uniform(1, 50)
            else:
                ltp = max(1, strike - spot_price + random.uniform(-20, 20)) if strike > spot_price else random.uniform(1, 50)
            
            lot_size = 50 if underlying == "NIFTY" else 25
            
            options.append({
                "underlying": underlying,
                "symbol": symbol,
                "strike": strike,
                "type": option_type,
                "expiry": expiry.strftime("%Y-%m-%d"),
                "ltp": round(ltp, 2),
                "volume": random.randint(5000, 100000),
                "oi": random.randint(50000, 500000),
                "lot": lot_size,
                "investment": round(ltp * lot_size, 2)
            })
    
    return options

# Mock Kite session for demo mode
class MockKiteSession:
    def __init__(self):
        self.connected = True
    
    def quote(self, instruments):
        """Mock quote method"""
        result = {}
        for instrument in instruments:
            if "NSE:" in instrument:
                result[instrument] = {
                    "last_price": random.uniform(24000, 26000),
                    "ohlc": {"close": random.uniform(24000, 26000)},
                    "volume": random.randint(100000, 1000000),
                    "oi": random.randint(50000, 500000)
                }
            elif "NFO:" in instrument:
                result[instrument] = {
                    "last_price": random.uniform(10, 500),
                    "ohlc": {"close": random.uniform(10, 500)},
                    "volume": random.randint(1000, 50000),
                    "oi": random.randint(10000, 100000)
                }
        return result
    
    def instruments(self, exchange):
        """Mock instruments method"""
        if exchange == "NFO":
            all_options = []
            for underlying in MOCK_UNDERLYINGS:
                all_options.extend(generate_mock_options_data(underlying))
            return all_options
        return []
    
    def historical_data(self, token, from_dt, to_dt, timeframe):
        """Mock historical data method"""
        return generate_mock_historical_data("MOCK", days=5)

def get_mock_kite_session():
    """Get a mock Kite session for demo purposes"""
    return MockKiteSession()
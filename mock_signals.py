import random
import datetime as dt
import uuid

def create_mock_signals():
    """Create mock Trinity signals for demo"""
    signals = []
    today = dt.datetime.now()
    underlyings = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
    
    for i in range(5):
        underlying = random.choice(underlyings)
        strike = random.randint(24000, 26000) if underlying == "NIFTY" else random.randint(50000, 54000)
        option_type = random.choice(["CE", "PE"])
        
        entry_price = round(random.uniform(50, 300), 2)
        sl_price = round(entry_price * 0.999, 2)  # 0.1% SL
        tp_price = round(entry_price * 1.001, 2)  # 0.1% TP
        rr = round((tp_price - entry_price) / (entry_price - sl_price), 2)
        
        signal_time = today.replace(
            hour=random.randint(9, 15),
            minute=random.randint(0, 59)
        )
        
        outcome = random.choice(["WIN", "LOSS", "PENDING", "PENDING"])
        
        signals.append({
            "id": str(uuid.uuid4()),
            "underlying": underlying,
            "contract": f"{underlying}25OCT{strike}{option_type}",
            "entry_price": entry_price,
            "sl": sl_price,
            "tp": tp_price,
            "rr": rr,
            "lot": 50,
            "outcome": outcome,
            "signal_time": signal_time,
            "created_at": signal_time
        })
    
    return signals
import random
import datetime as dt
import uuid

def create_mock_signals():
    """Create mock Trinity signals for demo with realistic data"""
    signals = []
    today = dt.datetime.now()
    
    # Create signals based on the user's example
    mock_data = [
        {"underlying": "DIVISLAB", "strike": 6100, "type": "CE", "entry": 50.8, "outcome": "WIN", "time": "09:30:00", "lot": 100},
        {"underlying": "AMBER", "strike": 8400, "type": "CE", "entry": 181.2, "outcome": "WIN", "time": "10:15:00", "lot": 100},
        {"underlying": "BRITANNIA", "strike": 5900, "type": "CE", "entry": 176.85, "outcome": "WIN", "time": "10:15:00", "lot": 125},
        {"underlying": "ANGELONE", "strike": 2250, "type": "PE", "entry": 81.05, "outcome": "WIN", "time": "10:30:00", "lot": 250},
        {"underlying": "BRITANNIA", "strike": 5900, "type": "PE", "entry": 80.0, "outcome": "WIN", "time": "12:00:00", "lot": 125},
        {"underlying": "ASIANPAINT", "strike": 2360, "type": "CE", "entry": 44.1, "outcome": "WIN", "time": "12:30:00", "lot": 250},
        {"underlying": "CAMS", "strike": 3800, "type": "CE", "entry": 129.5, "outcome": "WIN", "time": "12:30:00", "lot": 150},
        {"underlying": "MPHASIS", "strike": 2800, "type": "CE", "entry": 83.0, "outcome": "WIN", "time": "12:45:00", "lot": 275},
        {"underlying": "PERSISTENT", "strike": 5300, "type": "CE", "entry": 163.3, "outcome": "WIN", "time": "13:15:00", "lot": 100},
        {"underlying": "HINDUNILVR", "strike": 2520, "type": "PE", "entry": 34.05, "outcome": "WIN", "time": "13:15:00", "lot": 300},
        {"underlying": "MAZDOCK", "strike": 2900, "type": "PE", "entry": 89.55, "outcome": "WIN", "time": "13:15:00", "lot": 175},
        {"underlying": "SIEMENS", "strike": 3250, "type": "CE", "entry": 77.0, "outcome": "WIN", "time": "13:30:00", "lot": 125},
        {"underlying": "SHREECEM", "strike": 29500, "type": "CE", "entry": 633.25, "outcome": "PENDING", "time": "14:15:00", "lot": 25},
        {"underlying": "BANKNIFTY", "strike": 56200, "type": "CE", "entry": 718.15, "outcome": "WIN", "time": "14:30:00", "lot": 35},
        {"underlying": "HAL", "strike": 4850, "type": "PE", "entry": 110.35, "outcome": "LOSS", "time": "09:30:00", "lot": 150},
        {"underlying": "BAJAJ-AUTO", "strike": 8900, "type": "CE", "entry": 174.55, "outcome": "WIN", "time": "10:45:00", "lot": 75},
        {"underlying": "DMART", "strike": 4300, "type": "PE", "entry": 126.8, "outcome": "LOSS", "time": "12:15:00", "lot": 150},
        {"underlying": "GODREJPROP", "strike": 2080, "type": "CE", "entry": 53.0, "outcome": "WIN", "time": "13:00:00", "lot": 275},
    ]
    
    for i, data in enumerate(mock_data):
        hour, minute, second = map(int, data["time"].split(":"))
        signal_time = today.replace(hour=hour, minute=minute, second=second)
        
        entry_price = data["entry"]
        sl_price = round(entry_price * 0.999, 2)  # 0.1% SL
        tp_price = round(entry_price * 1.001, 2)  # 0.1% TP
        rr = round((tp_price - entry_price) / (entry_price - sl_price), 2) if entry_price > sl_price else 1.0
        
        signals.append({
            "id": str(uuid.uuid4()),
            "underlying": data["underlying"],
            "contract": f"{data['underlying']}25OCT{data['strike']}{data['type']}",
            "entry_price": entry_price,
            "sl": sl_price,
            "tp": tp_price,
            "rr": rr,
            "lot": data["lot"],
            "outcome": data["outcome"],
            "signal_time": signal_time,
            "created_at": signal_time
        })
    
    return signals
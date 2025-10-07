import random
import datetime as dt
import uuid

def create_mock_signals():
    """Create mock Trinity signals for demo with proper market hours timing"""
    signals = []
    
    # Use today's date with IST timezone
    import pytz
    IST = pytz.timezone('Asia/Kolkata')
    today = dt.datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Market hours: 9:15 AM to 3:30 PM IST
    # 15-minute candles: 9:15, 9:30, 9:45, 10:00, 10:15, 10:30, 10:45, 11:00, etc.
    
    # Generate signals only at 15-minute intervals during market hours
    market_start = today.replace(hour=9, minute=15)  # 9:15 AM IST
    market_end = today.replace(hour=15, minute=30)   # 3:30 PM IST
    
    # Valid 15-minute signal times (only during market hours)
    valid_times = []
    current_time = market_start
    while current_time <= market_end:
        valid_times.append(current_time)
        current_time += dt.timedelta(minutes=15)
    
    # Ensure we have enough valid times
    print(f"DEBUG: Generated {len(valid_times)} valid market time slots")
    print(f"DEBUG: Market times from {valid_times[0]} to {valid_times[-1]}")
    
    # Create signals ONLY during market hours with correct indices
    mock_data = [
        {"underlying": "DIVISLAB", "strike": 6100, "type": "CE", "entry": 50.8, "outcome": "WIN", "time_index": 1, "lot": 100},    # 9:30
        {"underlying": "AMBER", "strike": 8400, "type": "CE", "entry": 181.2, "outcome": "WIN", "time_index": 4, "lot": 100},     # 10:15  
        {"underlying": "BRITANNIA", "strike": 5900, "type": "CE", "entry": 176.85, "outcome": "WIN", "time_index": 4, "lot": 125}, # 10:15
        {"underlying": "ANGELONE", "strike": 2250, "type": "PE", "entry": 81.05, "outcome": "WIN", "time_index": 5, "lot": 250},   # 10:30
        {"underlying": "BRITANNIA", "strike": 5900, "type": "PE", "entry": 80.0, "outcome": "WIN", "time_index": 11, "lot": 125},  # 12:00
        {"underlying": "ASIANPAINT", "strike": 2360, "type": "CE", "entry": 44.1, "outcome": "WIN", "time_index": 13, "lot": 250}, # 12:30
        {"underlying": "CAMS", "strike": 3800, "type": "CE", "entry": 129.5, "outcome": "WIN", "time_index": 13, "lot": 150},      # 12:30
        {"underlying": "MPHASIS", "strike": 2800, "type": "CE", "entry": 83.0, "outcome": "WIN", "time_index": 14, "lot": 275},    # 12:45
        {"underlying": "PERSISTENT", "strike": 5300, "type": "CE", "entry": 163.3, "outcome": "WIN", "time_index": 16, "lot": 100}, # 13:15
        {"underlying": "HINDUNILVR", "strike": 2520, "type": "PE", "entry": 34.05, "outcome": "WIN", "time_index": 16, "lot": 300}, # 13:15
        {"underlying": "MAZDOCK", "strike": 2900, "type": "PE", "entry": 89.55, "outcome": "WIN", "time_index": 16, "lot": 175},    # 13:15
        {"underlying": "SIEMENS", "strike": 3250, "type": "CE", "entry": 77.0, "outcome": "WIN", "time_index": 17, "lot": 125},     # 13:30
        {"underlying": "SHREECEM", "strike": 29500, "type": "CE", "entry": 633.25, "outcome": "PENDING", "time_index": 20, "lot": 25}, # 14:15
        {"underlying": "BANKNIFTY", "strike": 56200, "type": "CE", "entry": 718.15, "outcome": "WIN", "time_index": 21, "lot": 35},    # 14:30  
        {"underlying": "HAL", "strike": 4850, "type": "PE", "entry": 110.35, "outcome": "LOSS", "time_index": 1, "lot": 150},       # 9:30
        {"underlying": "BAJAJ-AUTO", "strike": 8900, "type": "CE", "entry": 174.55, "outcome": "WIN", "time_index": 6, "lot": 75},  # 10:45
        {"underlying": "DMART", "strike": 4300, "type": "PE", "entry": 126.8, "outcome": "LOSS", "time_index": 12, "lot": 150},     # 12:15
        {"underlying": "GODREJPROP", "strike": 2080, "type": "CE", "entry": 53.0, "outcome": "WIN", "time_index": 15, "lot": 275},  # 13:00
    ]
    
    for data in mock_data:
        # Validate time_index to avoid out of bounds error
        if data["time_index"] >= len(valid_times):
            print(f"WARNING: time_index {data['time_index']} out of range for {data['underlying']}")
            continue
            
        # Get the exact 15-minute candle time
        signal_time = valid_times[data["time_index"]]
        
        entry_price = data["entry"]
        
        # Calculate SL and TP according to original Trinity logic
        sl_pct = 0.1 / 100.0  # 0.1% -> 0.001
        tp_pct = 0.1 / 100.0  # 0.1% -> 0.001
        
        sl_price = round(entry_price * (1 - sl_pct), 2)
        
        # TP based on Buy-Side Liquidity (BSL) as per original code
        # For mock data, assume BSL is higher than entry (typical bullish scenario)
        buy_liq = entry_price * 1.15  # Mock BSL 15% above entry
        tp_price = round(buy_liq * (1 - tp_pct), 2)  # TP slightly below BSL
        
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
            "signal_time": signal_time.isoformat(),  # Convert to ISO string
            "created_at": signal_time.isoformat()    # Convert to ISO string
        })
        
        print(f"DEBUG: {data['underlying']} signal at index {data['time_index']} -> {signal_time.strftime('%H:%M:%S')}")
    
    return signals
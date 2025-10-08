#!/usr/bin/env python3
"""
Create signals that ACTUALLY use the SL/TP settings from frontend
"""
import asyncio
import motor.motor_asyncio
from datetime import datetime
import pytz
import requests

IST = pytz.timezone('Asia/Kolkata')
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
db = client.trinity_scanner

async def create_signals_with_current_settings():
    """Create signals using the ACTUAL settings from frontend"""
    
    try:
        # Get current settings from backend API
        response = requests.get("https://wealth-scanner-2.preview.emergentagent.com/api/scanner/config", timeout=10)
        config = response.json()
        
        sl_pct = config.get("sl_percentage", 1.0)  # Default 1% if not found
        tp_pct = config.get("tp_percentage", 2.0)  # Default 2% if not found
        
        print(f"📊 Using ACTUAL settings from frontend:")
        print(f"   SL%: {sl_pct}%")
        print(f"   TP%: {tp_pct}%")
        
    except Exception as e:
        print(f"⚠️ Could not get frontend settings: {e}")
        print("Using default: SL=1%, TP=2%")
        sl_pct = 1.0
        tp_pct = 2.0
    
    # Clear old signals
    await db.signals.delete_many({})
    print("✅ Cleared old signals")
    
    # Create NEW signals with CURRENT SL/TP settings
    test_signals = [
        {"entry": 50.80, "symbol": "DIVISLAB25OCT6100CE", "underlying": "DIVISLAB"},
        {"entry": 100.25, "symbol": "RELIANCE25OCT1380CE", "underlying": "RELIANCE"}, 
        {"entry": 75.50, "symbol": "ICICIBANK25OCT1380CE", "underlying": "ICICIBANK"},
        {"entry": 200.75, "symbol": "HDFCBANK25OCT1500CE", "underlying": "HDFCBANK"}
    ]
    
    signals = []
    
    for i, test in enumerate(test_signals):
        entry_price = test["entry"]
        
        # 🎯 CALCULATE SL/TP USING ACTUAL SETTINGS
        sl_price = round(entry_price * (1 - sl_pct/100), 2)
        tp_price = round(entry_price * (1 + tp_pct/100), 2)
        
        # Create different outcomes for testing
        if i % 3 == 0:  # WIN
            outcome = "WIN"
            exit_price = tp_price
        elif i % 3 == 1:  # LOSS
            outcome = "LOSS" 
            exit_price = sl_price
        else:  # PENDING
            outcome = "PENDING"
            exit_price = None
        
        signal = {
            "id": f"live_signal_{i}",
            "underlying": test["underlying"],
            "contract": test["symbol"],
            "entry_price": entry_price,
            "sl": sl_price,
            "tp": tp_price,
            "outcome": outcome,
            "signal_time": datetime.now(IST),
            "created_at": datetime.now(IST),
            "lot": 100,
            "exit_price": exit_price
        }
        
        signals.append(signal)
        
        print(f"📈 {test['symbol']}")
        print(f"   Entry: ₹{entry_price} | SL: ₹{sl_price} ({sl_pct}%) | TP: ₹{tp_price} ({tp_pct}%)")
        print(f"   Outcome: {outcome}")
    
    # Insert signals
    result = await db.signals.insert_many(signals)
    print(f"\n✅ Created {len(result.inserted_ids)} signals with CURRENT settings")
    
    # Calculate expected stats
    wins = len([s for s in signals if s["outcome"] == "WIN"])
    losses = len([s for s in signals if s["outcome"] == "LOSS"])
    
    total_pnl = 0.0
    for signal in signals:
        if signal["exit_price"]:
            pnl = (signal["exit_price"] - signal["entry_price"]) * signal["lot"]
            total_pnl += pnl
    
    print(f"\n📊 EXPECTED STATS:")
    print(f"Total: {len(signals)}, Wins: {wins}, Losses: {losses}, P&L: ₹{total_pnl}")
    
    return True

async def main():
    print("🎯 Creating signals with ACTUAL SL/TP settings...")
    success = await create_signals_with_current_settings()
    
    if success:
        print("\n✅ Signals created with current frontend settings!")
        print("🔄 Now refresh the frontend to see updated signals")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Simple, direct outcome monitoring test - exactly as user described
"""
import asyncio
import motor.motor_asyncio
from datetime import datetime, timezone
import pytz

IST = pytz.timezone('Asia/Kolkata')

# MongoDB connection
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
db = client.trinity_scanner

async def create_simple_test_signals():
    """Create simple test signals with clear outcomes"""
    
    # Clear existing data
    await db.signals.delete_many({})
    print("✅ Cleared existing signals")
    
    # Simple test signals - exactly as user described logic
    signals = [
        # Signal 1: TP hit first = WIN
        {
            "id": "simple_001",
            "underlying": "NIFTY",
            "contract": "NIFTY25OCT25100CE",
            "entry_price": 50.0,
            "sl": 45.0,           # SL at 45
            "tp": 60.0,           # TP at 60
            "outcome": "WIN",      # TP (60) hit first = WIN
            "signal_time": datetime.now(IST),
            "created_at": datetime.now(IST),
            "exit_price": 60.0,   # Price hit TP level
            "lot": 75
        },
        
        # Signal 2: SL hit first = LOSS  
        {
            "id": "simple_002", 
            "underlying": "BANKNIFTY",
            "contract": "BANKNIFTY25OCT56200CE",
            "entry_price": 700.0,
            "sl": 650.0,          # SL at 650
            "tp": 800.0,          # TP at 800
            "outcome": "LOSS",     # SL (650) hit first = LOSS
            "signal_time": datetime.now(IST),
            "created_at": datetime.now(IST),
            "exit_price": 650.0,  # Price hit SL level
            "lot": 35
        },
        
        # Signal 3: Neither hit yet = PENDING
        {
            "id": "simple_003",
            "underlying": "RELIANCE", 
            "contract": "RELIANCE25OCT1380CE",
            "entry_price": 30.0,
            "sl": 27.0,           # SL at 27
            "tp": 36.0,           # TP at 36
            "outcome": "PENDING",  # Neither hit = PENDING
            "signal_time": datetime.now(IST),
            "created_at": datetime.now(IST),
            "lot": 500
        }
    ]
    
    # Insert signals
    result = await db.signals.insert_many(signals)
    print(f"✅ Created {len(result.inserted_ids)} simple test signals")
    
    # Calculate simple stats
    total = len(signals)
    wins = len([s for s in signals if s["outcome"] == "WIN"])
    losses = len([s for s in signals if s["outcome"] == "LOSS"])
    
    # Calculate P&L (simple: exit_price - entry_price) * lot
    total_pnl = 0.0
    for signal in signals:
        if signal["outcome"] == "WIN":
            pnl = (signal["exit_price"] - signal["entry_price"]) * signal["lot"]
            total_pnl += pnl
            print(f"✅ WIN: {signal['contract']} = +₹{pnl} (TP hit at ₹{signal['exit_price']})")
        elif signal["outcome"] == "LOSS":
            pnl = (signal["exit_price"] - signal["entry_price"]) * signal["lot"]  # Will be negative
            total_pnl += pnl
            print(f"❌ LOSS: {signal['contract']} = ₹{pnl} (SL hit at ₹{signal['exit_price']})")
        else:
            print(f"⏳ PENDING: {signal['contract']} (waiting for TP ₹{signal['tp']} or SL ₹{signal['sl']})")
    
    print(f"\n📊 SIMPLE STATS:")
    print(f"Total Signals: {total}")
    print(f"Winning Signals: {wins}")
    print(f"Losing Signals: {losses}")  
    print(f"Total P&L: ₹{total_pnl}")
    
    return True

async def main():
    print("🎯 Creating SIMPLE outcome test - as user described...")
    print("Logic: SL hit first = LOSS, TP hit first = WIN, neither = PENDING")
    
    success = await create_simple_test_signals()
    
    if success:
        print("\n✅ Simple test created!")
        print("Expected frontend display:")
        print("- Total: 3, Wins: 1, Losses: 1, P&L: ₹2250")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
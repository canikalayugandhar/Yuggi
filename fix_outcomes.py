#!/usr/bin/env python3
"""
Direct database script to create test signals and update outcomes
"""
import asyncio
import motor.motor_asyncio
from datetime import datetime, timezone
import pytz
import uuid

IST = pytz.timezone('Asia/Kolkata')

# MongoDB connection
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
db = client.trinity_scanner

async def create_test_signals():
    """Create test signals directly in database"""
    
    # Create 3 test signals with different outcomes
    signals = [
        {
            "id": str(uuid.uuid4()),
            "underlying": "NIFTY",
            "contract": "NIFTY25OCT25100CE", 
            "entry_price": 50.0,
            "sl": 45.0,
            "tp": 60.0,
            "rr": 2.0,
            "lot": 75,
            "outcome": "WIN",  # This one will be a winner
            "signal_time": datetime.now(IST),
            "created_at": datetime.now(IST),
            "exit_price": 60.0,  # Hit TP
            "hit_time": datetime.now(IST)
        },
        {
            "id": str(uuid.uuid4()),
            "underlying": "BANKNIFTY", 
            "contract": "BANKNIFTY25OCT56200CE",
            "entry_price": 700.0,
            "sl": 650.0,
            "tp": 800.0,
            "rr": 2.0,
            "lot": 35,
            "outcome": "LOSS",  # This one will be a loss
            "signal_time": datetime.now(IST),
            "created_at": datetime.now(IST),
            "exit_price": 650.0,  # Hit SL
            "hit_time": datetime.now(IST)
        },
        {
            "id": str(uuid.uuid4()),
            "underlying": "RELIANCE",
            "contract": "RELIANCE25OCT1380CE",
            "entry_price": 30.0,
            "sl": 27.0,
            "tp": 36.0,
            "rr": 2.0,
            "lot": 500,
            "outcome": "PENDING",  # This one is still pending
            "signal_time": datetime.now(IST),
            "created_at": datetime.now(IST)
        },
        {
            "id": str(uuid.uuid4()),
            "underlying": "ICICIBANK",
            "contract": "ICICIBANK25OCT1380CE",
            "entry_price": 25.0,
            "sl": 22.5,
            "tp": 30.0,
            "rr": 2.2,
            "lot": 700,
            "outcome": "WIN",  # Another winner
            "signal_time": datetime.now(IST),
            "created_at": datetime.now(IST),
            "exit_price": 30.0,  # Hit TP
            "hit_time": datetime.now(IST)
        }
    ]
    
    try:
        # Clear existing signals first
        await db.signals.delete_many({})
        print("✅ Cleared existing signals")
        
        # Insert test signals
        result = await db.signals.insert_many(signals)
        print(f"✅ Created {len(result.inserted_ids)} test signals")
        
        # Calculate stats
        total_signals = len(signals)
        winning_signals = len([s for s in signals if s["outcome"] == "WIN"])
        losing_signals = len([s for s in signals if s["outcome"] == "LOSS"])
        pending_signals = len([s for s in signals if s["outcome"] == "PENDING"])
        
        # Calculate P&L
        total_pnl = 0.0
        for signal in signals:
            if signal["outcome"] == "WIN":
                pnl = (signal["exit_price"] - signal["entry_price"]) * signal["lot"]
                total_pnl += pnl
                print(f"WIN: {signal['contract']} = +₹{pnl}")
            elif signal["outcome"] == "LOSS":
                pnl = (signal["exit_price"] - signal["entry_price"]) * signal["lot"]  # This will be negative
                total_pnl += pnl
                print(f"LOSS: {signal['contract']} = ₹{pnl}")
        
        print(f"\n📊 EXPECTED STATS:")
        print(f"Total Signals: {total_signals}")
        print(f"Winning Signals: {winning_signals}")
        print(f"Losing Signals: {losing_signals}")
        print(f"Pending Signals: {pending_signals}")
        print(f"Total P&L: ₹{total_pnl}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating test signals: {e}")
        return False

async def main():
    print("🎯 Creating test signals for outcome monitoring...")
    success = await create_test_signals()
    
    if success:
        print("\n✅ Test signals created successfully!")
        print("🔄 Refresh the frontend to see updated stats")
    else:
        print("\n❌ Failed to create test signals")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
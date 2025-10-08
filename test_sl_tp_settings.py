#!/usr/bin/env python3
"""
Test SL% and TP% settings are working correctly
"""
import asyncio
import motor.motor_asyncio
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
db = client.trinity_scanner

async def test_sl_tp_settings():
    """Test SL/TP settings with different percentages"""
    
    await db.signals.delete_many({})
    print("✅ Cleared existing signals")
    
    # Test signals with different SL/TP percentages
    test_cases = [
        {
            "entry_price": 100.0,
            "sl_pct": 5.0,   # 5% SL
            "tp_pct": 10.0,  # 10% TP
            "expected_sl": 95.0,    # 100 * (1 - 0.05) = 95
            "expected_tp": 110.0,   # 100 * (1 + 0.10) = 110
        },
        {
            "entry_price": 50.0,
            "sl_pct": 3.0,   # 3% SL  
            "tp_pct": 6.0,   # 6% TP
            "expected_sl": 48.5,    # 50 * (1 - 0.03) = 48.5
            "expected_tp": 53.0,    # 50 * (1 + 0.06) = 53
        },
        {
            "entry_price": 200.0,
            "sl_pct": 2.0,   # 2% SL
            "tp_pct": 4.0,   # 4% TP  
            "expected_sl": 196.0,   # 200 * (1 - 0.02) = 196
            "expected_tp": 208.0,   # 200 * (1 + 0.04) = 208
        }
    ]
    
    signals = []
    
    for i, case in enumerate(test_cases):
        # Test WIN scenario (TP hit)
        win_signal = {
            "id": f"test_sl_tp_win_{i}",
            "underlying": "TEST",
            "contract": f"TEST{i}CE",
            "entry_price": case["entry_price"],
            "sl": case["expected_sl"],
            "tp": case["expected_tp"], 
            "outcome": "WIN",
            "exit_price": case["expected_tp"],  # TP hit
            "signal_time": datetime.now(IST),
            "created_at": datetime.now(IST),
            "lot": 100
        }
        
        # Test LOSS scenario (SL hit)
        loss_signal = {
            "id": f"test_sl_tp_loss_{i}",
            "underlying": "TEST",
            "contract": f"TEST{i}PE",
            "entry_price": case["entry_price"],
            "sl": case["expected_sl"],
            "tp": case["expected_tp"],
            "outcome": "LOSS", 
            "exit_price": case["expected_sl"],  # SL hit
            "signal_time": datetime.now(IST),
            "created_at": datetime.now(IST),
            "lot": 100
        }
        
        signals.extend([win_signal, loss_signal])
        
        print(f"📊 Test Case {i+1}:")
        print(f"   Entry: ₹{case['entry_price']} | SL: {case['sl_pct']}% | TP: {case['tp_pct']}%")
        print(f"   Expected SL: ₹{case['expected_sl']} | Expected TP: ₹{case['expected_tp']}")
        print(f"   WIN P&L: +₹{(case['expected_tp'] - case['entry_price']) * 100}")
        print(f"   LOSS P&L: ₹{(case['expected_sl'] - case['entry_price']) * 100}")
    
    # Insert test signals
    result = await db.signals.insert_many(signals)
    print(f"\n✅ Created {len(result.inserted_ids)} test signals")
    
    # Calculate expected stats
    total_pnl = 0.0
    wins = 0
    losses = 0
    
    for signal in signals:
        if signal["outcome"] == "WIN":
            wins += 1
            pnl = (signal["exit_price"] - signal["entry_price"]) * signal["lot"]
            total_pnl += pnl
        elif signal["outcome"] == "LOSS":
            losses += 1
            pnl = (signal["exit_price"] - signal["entry_price"]) * signal["lot"]  # Will be negative
            total_pnl += pnl
    
    print(f"\n📊 EXPECTED FRONTEND STATS:")
    print(f"Total Signals: {len(signals)}")
    print(f"Winning Signals: {wins}")
    print(f"Losing Signals: {losses}")
    print(f"Total P&L: ₹{total_pnl}")
    
    return True

async def main():
    print("🎯 Testing SL% and TP% Settings...")
    success = await test_sl_tp_settings()
    
    if success:
        print("\n✅ SL/TP test signals created!")
        print("🔄 Refresh frontend to see if stats update correctly")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
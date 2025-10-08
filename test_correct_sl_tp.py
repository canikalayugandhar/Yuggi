#!/usr/bin/env python3
"""
Test the CORRECT SL/TP calculation using POI LOW and Bullish Liquidity
"""
import asyncio
import motor.motor_asyncio
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
db = client.trinity_scanner

async def test_correct_sl_tp_logic():
    """Test SL/TP using correct SMC logic"""
    
    await db.signals.delete_many({})
    print("✅ Cleared existing signals")
    
    print("🎯 Testing CORRECT SL/TP Logic:")
    print("   SL = POI LOW - SL%")
    print("   TP = Bullish Liquidity - TP%")
    print()
    
    # Example with 5% SL and 3% TP (as user mentioned)
    sl_pct = 5.0  # 5%
    tp_pct = 3.0  # 3%
    
    # Test cases with realistic SMC values
    test_cases = [
        {
            "entry_price": 50.80,
            "poi_low": 49.50,      # POI LOW level
            "bullish_liq": 55.20,   # Bullish Liquidity level
            "contract": "DIVISLAB25OCT6100CE",
            "underlying": "DIVISLAB"
        },
        {
            "entry_price": 100.25,
            "poi_low": 98.75,      # POI LOW level  
            "bullish_liq": 105.60,  # Bullish Liquidity level
            "contract": "RELIANCE25OCT1380CE",
            "underlying": "RELIANCE"
        }
    ]
    
    signals = []
    
    for i, case in enumerate(test_cases):
        # Calculate using CORRECT logic
        sl_price = round(case["poi_low"] * (1 - sl_pct/100), 2)      # POI LOW - SL%
        tp_price = round(case["bullish_liq"] * (1 - tp_pct/100), 2)  # Bullish Liq - TP%
        
        signal = {
            "id": f"correct_test_{i}",
            "underlying": case["underlying"],
            "contract": case["contract"],
            "entry_price": case["entry_price"],
            "sl": sl_price,
            "tp": tp_price,
            "outcome": "PENDING",
            "signal_time": datetime.now(IST),
            "created_at": datetime.now(IST),
            "lot": 100,
            "poi_low": case["poi_low"],
            "bullish_liquidity": case["bullish_liq"]
        }
        
        signals.append(signal)
        
        print(f"📊 {case['contract']}:")
        print(f"   Entry Price: ₹{case['entry_price']}")
        print(f"   POI LOW: ₹{case['poi_low']}")
        print(f"   Bullish Liquidity: ₹{case['bullish_liq']}")
        print(f"   SL = ₹{case['poi_low']} - {sl_pct}% = ₹{sl_price}")
        print(f"   TP = ₹{case['bullish_liq']} - {tp_pct}% = ₹{tp_price}")
        print(f"   Result: SL ₹{sl_price}, TP ₹{tp_price}")
        print()
    
    # Insert test signals
    result = await db.signals.insert_many(signals)
    print(f"✅ Created {len(result.inserted_ids)} signals with CORRECT SMC logic")
    
    print("📱 Now refresh frontend to see signals with correct SL/TP calculations!")
    
    return True

async def main():
    print("🎯 Testing CORRECT SMC SL/TP Logic...")
    success = await test_correct_sl_tp_logic()
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
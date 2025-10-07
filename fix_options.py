#!/usr/bin/env python3
"""
Direct database script to fix options display
"""
import asyncio
import motor.motor_asyncio
from datetime import datetime, date
import random

# MongoDB connection
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
db = client.trinity_scanner

async def create_sample_options():
    """Create sample ATM options directly in database"""
    
    options = []
    
    # NIFTY options
    nifty_strikes = [25050, 25100, 25150, 25200]
    for strike in nifty_strikes:
        options.extend([
            {
                "underlying": "NIFTY",
                "symbol": f"NIFTY25OCT{strike}CE",
                "strike": strike,
                "type": "CE",
                "expiry": "2025-10-28",
                "ltp": round(random.uniform(10, 100), 2),
                "volume": random.randint(100000, 5000000),
                "oi": random.randint(50000, 2000000),
                "lot": 75,
                "investment": 0
            },
            {
                "underlying": "NIFTY",
                "symbol": f"NIFTY25OCT{strike}PE",
                "strike": strike,
                "type": "PE", 
                "expiry": "2025-10-28",
                "ltp": round(random.uniform(10, 100), 2),
                "volume": random.randint(100000, 5000000),
                "oi": random.randint(50000, 2000000),
                "lot": 75,
                "investment": 0
            }
        ])
    
    # BANKNIFTY options
    banknifty_strikes = [56000, 56100, 56200, 56300]
    for strike in banknifty_strikes:
        options.extend([
            {
                "underlying": "BANKNIFTY",
                "symbol": f"BANKNIFTY25OCT{strike}CE",
                "strike": strike,
                "type": "CE",
                "expiry": "2025-10-28",
                "ltp": round(random.uniform(100, 800), 2),
                "volume": random.randint(50000, 3000000),
                "oi": random.randint(25000, 1000000),
                "lot": 35,
                "investment": 0
            },
            {
                "underlying": "BANKNIFTY",
                "symbol": f"BANKNIFTY25OCT{strike}PE",
                "strike": strike,
                "type": "PE",
                "expiry": "2025-10-28",
                "ltp": round(random.uniform(100, 800), 2),
                "volume": random.randint(50000, 3000000),
                "oi": random.randint(25000, 1000000),
                "lot": 35,
                "investment": 0
            }
        ])
    
    # Calculate investment for each option
    for option in options:
        option["investment"] = round(option["ltp"] * option["lot"], 2)
    
    try:
        # Clear existing options
        await db.options.delete_many({})
        print("✅ Cleared existing options")
        
        # Insert sample options
        result = await db.options.insert_many(options)
        print(f"✅ Created {len(result.inserted_ids)} sample options")
        
        # Print first few for verification
        for i, option in enumerate(options[:5]):
            print(f"Option {i+1}: {option['symbol']} @ ₹{option['ltp']} (Investment: ₹{option['investment']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample options: {e}")
        return False

async def main():
    print("📋 Creating sample options for ATM options display...")
    success = await create_sample_options()
    
    if success:
        print(f"\n✅ Sample options created successfully!")
        print("🔄 Refresh the Options tab to see data")
    else:
        print("\n❌ Failed to create sample options")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
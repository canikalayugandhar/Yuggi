#!/usr/bin/env python3
"""
Clear ALL old data completely - start fresh for market opening
"""
import asyncio
import motor.motor_asyncio

async def clear_everything():
    """Clear all old signals and options data"""
    
    print("🧹 CLEARING ALL OLD DATA...")
    
    # Connect to database
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.trinity_scanner
    
    # 1. Clear ALL signals
    result_signals = await db.signals.delete_many({})
    print(f"✅ Cleared {result_signals.deleted_count} old signals")
    
    # 2. Clear ALL options  
    result_options = await db.options.delete_many({})
    print(f"✅ Cleared {result_options.deleted_count} old options")
    
    # 3. Clear any other collections that might have old data
    collections = await db.list_collection_names()
    for collection_name in collections:
        if collection_name not in ['signals', 'options']:
            collection = db[collection_name]
            result = await collection.delete_many({})
            if result.deleted_count > 0:
                print(f"✅ Cleared {result.deleted_count} items from {collection_name}")
    
    # 4. Verify everything is clean
    signal_count = await db.signals.count_documents({})
    option_count = await db.options.count_documents({})
    
    print(f"\n📊 VERIFICATION:")
    print(f"   Signals in database: {signal_count}")
    print(f"   Options in database: {option_count}")
    
    if signal_count == 0 and option_count == 0:
        print(f"✅ Database is completely clean!")
    else:
        print(f"❌ Still some data remaining")
    
    client.close()
    return signal_count == 0

async def main():
    print("🧹 CLEARING ALL OLD DATA FOR FRESH START...")
    success = await clear_everything()
    
    if success:
        print(f"\n🎯 SYSTEM READY:")
        print(f"   - All old data cleared")
        print(f"   - Frontend should show 0 signals")
        print(f"   - Fresh start when market opens at 9:15 AM")
    
if __name__ == "__main__":
    asyncio.run(main())
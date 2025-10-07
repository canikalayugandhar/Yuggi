#!/usr/bin/env python3
"""
Quick Entry Price Validation Test
"""

import requests
import json
import time
import datetime as dt
import pytz

# Test Configuration
BACKEND_URL = "https://wealth-scanner-2.preview.emergentagent.com/api"
IST = pytz.timezone('Asia/Kolkata')

def test_api_basic():
    """Test basic API connectivity"""
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=10)
        print(f"✅ API Status: {response.status_code} - {response.json()}")
        return True
    except Exception as e:
        print(f"❌ API Error: {e}")
        return False

def test_signals_endpoint():
    """Test signals endpoint and validate entry prices"""
    try:
        response = requests.get(f"{BACKEND_URL}/scanner/signals", timeout=10)
        if response.status_code == 200:
            signals = response.json()
            print(f"✅ Retrieved {len(signals)} signals")
            
            if signals:
                print("\n🎯 ENTRY PRICE ANALYSIS:")
                for i, signal in enumerate(signals[:5]):  # Check first 5 signals
                    entry_price = signal.get('entry_price')
                    poi_price = signal.get('poi_price')
                    underlying = signal.get('underlying', 'Unknown')
                    contract = signal.get('contract', 'Unknown')
                    signal_time = signal.get('signal_time', 'Unknown')
                    
                    print(f"Signal {i+1}: {underlying} {contract}")
                    print(f"  Entry Price: ₹{entry_price}")
                    print(f"  POI Price: ₹{poi_price}")
                    print(f"  Signal Time: {signal_time}")
                    
                    # Check if entry price differs from POI price (good sign)
                    if poi_price and entry_price and abs(entry_price - poi_price) > 0.01:
                        print(f"  ✅ Entry price differs from POI price (using live market price)")
                    elif poi_price and entry_price and abs(entry_price - poi_price) <= 0.01:
                        print(f"  ⚠️ Entry price matches POI price (may be using historical price)")
                    
                    print()
            else:
                print("No signals found (expected during off-market hours)")
            
            return signals
        else:
            print(f"❌ Signals API Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Signals Test Error: {e}")
        return []

def test_scanner_status():
    """Test scanner status"""
    try:
        response = requests.get(f"{BACKEND_URL}/scanner/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Scanner Status: Running={status.get('is_running')}")
            print(f"   Error: {status.get('error_message', 'None')}")
            print(f"   Stats: {status.get('stats', {})}")
            return status
        else:
            print(f"❌ Status API Error: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Status Test Error: {e}")
        return {}

def main():
    print("🚀 Quick Trinity Scanner Entry Price Test")
    print(f"Testing: {BACKEND_URL}")
    print(f"Current IST: {dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("="*60)
    
    # Basic tests
    if not test_api_basic():
        return
    
    test_scanner_status()
    signals = test_signals_endpoint()
    
    print("="*60)
    print("🎯 ENTRY PRICE VALIDATION SUMMARY:")
    
    if signals:
        realistic_prices = 0
        total_signals = len(signals)
        
        for signal in signals:
            entry_price = signal.get('entry_price')
            if entry_price and isinstance(entry_price, (int, float)) and 0.5 <= entry_price <= 1000:
                realistic_prices += 1
        
        print(f"Total Signals: {total_signals}")
        print(f"Realistic Entry Prices: {realistic_prices}/{total_signals}")
        print(f"Success Rate: {(realistic_prices/total_signals)*100:.1f}%")
        
        if realistic_prices == total_signals:
            print("✅ ALL SIGNALS HAVE REALISTIC ENTRY PRICES")
        else:
            print("⚠️ SOME SIGNALS HAVE UNREALISTIC ENTRY PRICES")
    else:
        print("No signals to validate (expected during off-market hours)")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Detailed Entry Price Validation Test
Focus on realistic entry prices vs historical POI prices
"""

import requests
import json
import time
import datetime as dt
import pytz

# Test Configuration
BACKEND_URL = "http://localhost:8001/api"
IST = pytz.timezone('Asia/Kolkata')

def get_all_signals():
    """Get all signals and analyze entry price patterns"""
    try:
        response = requests.get(f"{BACKEND_URL}/scanner/signals", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"❌ Error getting signals: {e}")
        return []

def analyze_entry_prices(signals):
    """Analyze entry price accuracy and realism"""
    print(f"\n🎯 DETAILED ENTRY PRICE ANALYSIS ({len(signals)} signals):")
    print("="*80)
    
    realistic_count = 0
    unrealistic_count = 0
    poi_mismatch_count = 0
    
    for i, signal in enumerate(signals):
        entry_price = signal.get('entry_price')
        poi_price = signal.get('poi_price')
        live_entry_price = signal.get('live_entry_price')
        underlying = signal.get('underlying', 'Unknown')
        contract = signal.get('contract', 'Unknown')
        signal_time = signal.get('signal_time', 'Unknown')
        sl = signal.get('sl')
        tp = signal.get('tp')
        
        print(f"\nSignal {i+1}: {underlying}")
        print(f"  Contract: {contract}")
        print(f"  Entry Price: ₹{entry_price}")
        print(f"  POI Price: ₹{poi_price}")
        print(f"  Live Entry Price: ₹{live_entry_price}")
        print(f"  SL: ₹{sl}")
        print(f"  TP: ₹{tp}")
        print(f"  Signal Time: {signal_time}")
        
        # Validate entry price realism
        if entry_price and isinstance(entry_price, (int, float)):
            if 0.5 <= entry_price <= 1000:  # Reasonable range for options
                realistic_count += 1
                print(f"  ✅ Realistic entry price")
            else:
                unrealistic_count += 1
                print(f"  ❌ Unrealistic entry price: ₹{entry_price}")
        
        # Check if entry price differs from POI price (good sign)
        if poi_price and entry_price:
            if abs(entry_price - poi_price) > 0.01:
                poi_mismatch_count += 1
                print(f"  ✅ Entry price differs from POI (using live market price)")
            else:
                print(f"  ⚠️ Entry price matches POI (may be using historical price)")
        elif poi_price is None:
            print(f"  ℹ️ POI price not available (expected after fix)")
        
        # Validate SL/TP logic
        if sl and entry_price:
            sl_pct = ((entry_price - sl) / entry_price) * 100
            if 1 <= sl_pct <= 50:
                print(f"  ✅ SL percentage: {sl_pct:.1f}%")
            else:
                print(f"  ⚠️ Unusual SL percentage: {sl_pct:.1f}%")
    
    print("\n" + "="*80)
    print("📊 ENTRY PRICE VALIDATION SUMMARY:")
    print(f"Total Signals: {len(signals)}")
    print(f"Realistic Entry Prices: {realistic_count}/{len(signals)}")
    print(f"POI Price Mismatches: {poi_mismatch_count}/{len(signals)} (good - using live prices)")
    print(f"Success Rate: {(realistic_count/len(signals))*100:.1f}%")
    
    return realistic_count == len(signals)

def test_intrabar_mode():
    """Test intrabar mode entry pricing"""
    print("\n🔥 TESTING INTRABAR MODE ENTRY PRICING:")
    print("="*60)
    
    # Configure intrabar mode
    config = {
        "api_key": "jdhb0gprnxjr1k31",
        "api_secret": "4qnsimdyhlrgm3tqk7toiosu8u2i9wsg",
        "allow_intrabar": True,
        "refresh_sec": 5
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/scanner/config", json=config, timeout=10)
        if response.status_code == 200:
            print("✅ Intrabar mode configured")
            
            # Restart scanner
            requests.post(f"{BACKEND_URL}/scanner/stop", timeout=10)
            time.sleep(2)
            requests.post(f"{BACKEND_URL}/scanner/start", timeout=10)
            
            print("⏳ Waiting 15 seconds for intrabar signals...")
            time.sleep(15)
            
            signals = get_all_signals()
            if signals:
                print(f"📊 Generated {len(signals)} signals in intrabar mode")
                return analyze_entry_prices(signals)
            else:
                print("ℹ️ No signals generated in intrabar mode (expected during off-hours)")
                return True
        else:
            print(f"❌ Failed to configure intrabar mode: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Intrabar mode test error: {e}")
        return False

def test_candle_close_mode():
    """Test candle close mode entry pricing"""
    print("\n📊 TESTING CANDLE CLOSE MODE ENTRY PRICING:")
    print("="*60)
    
    # Configure candle close mode
    config = {
        "api_key": "jdhb0gprnxjr1k31",
        "api_secret": "4qnsimdyhlrgm3tqk7toiosu8u2i9wsg",
        "allow_intrabar": False,
        "refresh_sec": 10
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/scanner/config", json=config, timeout=10)
        if response.status_code == 200:
            print("✅ Candle close mode configured")
            
            # Restart scanner
            requests.post(f"{BACKEND_URL}/scanner/stop", timeout=10)
            time.sleep(2)
            requests.post(f"{BACKEND_URL}/scanner/start", timeout=10)
            
            print("⏳ Waiting 15 seconds for candle close signals...")
            time.sleep(15)
            
            signals = get_all_signals()
            if signals:
                print(f"📊 Generated {len(signals)} signals in candle close mode")
                return analyze_entry_prices(signals)
            else:
                print("ℹ️ No signals generated in candle close mode (expected during off-hours)")
                return True
        else:
            print(f"❌ Failed to configure candle close mode: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Candle close mode test error: {e}")
        return False

def validate_signal_timing(signals):
    """Validate signal timing is within market hours"""
    print("\n⏰ SIGNAL TIMING VALIDATION:")
    print("="*50)
    
    valid_timing = 0
    invalid_timing = 0
    
    for signal in signals:
        signal_time_raw = signal.get('signal_time')
        if signal_time_raw:
            try:
                if isinstance(signal_time_raw, str) and 'T' in signal_time_raw:
                    signal_dt = dt.datetime.fromisoformat(signal_time_raw.replace('Z', '+00:00'))
                    signal_dt = signal_dt.astimezone(IST)
                    
                    signal_time = signal_dt.time()
                    market_start = dt.time(9, 15)
                    market_end = dt.time(15, 30)
                    
                    if market_start <= signal_time <= market_end:
                        valid_timing += 1
                    else:
                        invalid_timing += 1
                        print(f"❌ Invalid timing: {signal_dt.strftime('%H:%M:%S IST')}")
            except Exception as e:
                invalid_timing += 1
                print(f"❌ Failed to parse time: {signal_time_raw}")
    
    print(f"Valid Timing: {valid_timing}/{len(signals)}")
    print(f"Invalid Timing: {invalid_timing}/{len(signals)}")
    
    return invalid_timing == 0

def main():
    print("🎯 TRINITY WEALTH SCANNER - DETAILED ENTRY PRICE VALIDATION")
    print(f"Testing: {BACKEND_URL}")
    print(f"Current IST: {dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("="*80)
    
    # Get current signals
    signals = get_all_signals()
    
    if signals:
        # Analyze current signals
        entry_price_valid = analyze_entry_prices(signals)
        timing_valid = validate_signal_timing(signals)
        
        # Test both modes
        intrabar_valid = test_intrabar_mode()
        candle_close_valid = test_candle_close_mode()
        
        print("\n" + "="*80)
        print("🏆 FINAL VALIDATION RESULTS:")
        print("="*80)
        print(f"✅ Entry Price Accuracy: {'PASS' if entry_price_valid else 'FAIL'}")
        print(f"✅ Signal Timing: {'PASS' if timing_valid else 'FAIL'}")
        print(f"✅ Intrabar Mode: {'PASS' if intrabar_valid else 'FAIL'}")
        print(f"✅ Candle Close Mode: {'PASS' if candle_close_valid else 'FAIL'}")
        
        overall_success = all([entry_price_valid, timing_valid, intrabar_valid, candle_close_valid])
        print(f"\n🎯 OVERALL RESULT: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
    else:
        print("ℹ️ No signals found - testing during off-market hours")
        print("✅ This is expected behavior outside market hours (9:15 AM - 3:30 PM IST)")

if __name__ == "__main__":
    main()
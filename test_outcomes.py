#!/usr/bin/env python3
"""
Test script to create signals and simulate outcomes for testing
"""
import asyncio
import requests
import json
from datetime import datetime, timezone
import pytz

IST = pytz.timezone('Asia/Kolkata')

BASE_URL = "https://wealth-scanner-2.preview.emergentagent.com/api"

def create_test_signal():
    """Create a test signal for outcome monitoring"""
    signal_data = {
        "id": "test_signal_001",
        "underlying": "NIFTY",
        "contract": "NIFTY25OCT25100CE",
        "entry_price": 50.0,
        "sl": 45.0,
        "tp": 60.0,
        "rr": 2.0,
        "lot": 75,
        "outcome": "PENDING",
        "signal_time": datetime.now(IST).isoformat(),
        "created_at": datetime.now(IST).isoformat()
    }
    
    try:
        response = requests.post(f"{BASE_URL}/scanner/test-signal", json=signal_data, timeout=10)
        print(f"Created test signal: {response.status_code}")
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"Error creating test signal: {e}")
        return None

def test_outcome_win():
    """Test WIN outcome"""
    try:
        response = requests.post(f"{BASE_URL}/scanner/test-outcome/test_signal_001/WIN", timeout=10)
        print(f"Test WIN outcome: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error testing WIN: {e}")

def test_outcome_loss():
    """Test LOSS outcome"""
    try:
        response = requests.post(f"{BASE_URL}/scanner/test-outcome/test_signal_001/LOSS", timeout=10)
        print(f"Test LOSS outcome: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error testing LOSS: {e}")

if __name__ == "__main__":
    print("Testing outcome monitoring system...")
    
    # Create test signal
    signal = create_test_signal()
    
    if signal:
        print("Created test signal successfully")
        
        # Test WIN outcome
        print("\nTesting WIN outcome...")
        test_outcome_win()
        
        # Wait a bit
        import time
        time.sleep(2)
        
        # Reset and test LOSS
        print("\nResetting and testing LOSS outcome...")
        # First create another signal
        signal_data = {
            "id": "test_signal_002", 
            "underlying": "BANKNIFTY",
            "contract": "BANKNIFTY25OCT56200CE",
            "entry_price": 700.0,
            "sl": 650.0,
            "tp": 800.0,
            "rr": 2.0,
            "lot": 35,
            "outcome": "PENDING",
            "signal_time": datetime.now(IST).isoformat(),
            "created_at": datetime.now(IST).isoformat()
        }
        
        try:
            response = requests.post(f"{BASE_URL}/scanner/test-signal", json=signal_data, timeout=10)
            print(f"Created second test signal: {response.status_code}")
            
            if response.status_code == 200:
                # Test LOSS
                response = requests.post(f"{BASE_URL}/scanner/test-outcome/test_signal_002/LOSS", timeout=10)
                print(f"Test LOSS outcome: {response.status_code}")
                if response.status_code == 200:
                    print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Error with second signal: {e}")
    else:
        print("Failed to create test signal")
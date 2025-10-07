#!/usr/bin/env python3
"""
Simple Trinity Wealth Scanner Backend Testing
Focus: WIN/LOSS Calculation Fix Validation
"""

import requests
import json
import time
import datetime as dt
import pytz
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test Configuration
BACKEND_URL = "https://wealth-scanner-2.preview.emergentagent.com/api"
IST = pytz.timezone('Asia/Kolkata')

def test_api_connectivity():
    """Test basic API connectivity"""
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ API connectivity: {data.get('message', 'OK')}")
            return True
        else:
            logger.error(f"❌ API connectivity failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ API connectivity failed: {str(e)}")
        return False

def test_scanner_status():
    """Test scanner status endpoint"""
    try:
        response = requests.get(f"{BACKEND_URL}/scanner/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            is_running = data.get('is_running', False)
            error_msg = data.get('error_message', 'None')
            stats = data.get('stats', {})
            logger.info(f"✅ Scanner status: Running={is_running}, Error={error_msg}")
            logger.info(f"   Stats: {stats}")
            return data
        else:
            logger.error(f"❌ Scanner status failed: HTTP {response.status_code}")
            return {}
    except Exception as e:
        logger.error(f"❌ Scanner status failed: {str(e)}")
        return {}

def test_signals_endpoint():
    """Test signals endpoint and analyze outcomes"""
    try:
        response = requests.get(f"{BACKEND_URL}/scanner/signals", timeout=10)
        if response.status_code == 200:
            signals = response.json()
            logger.info(f"✅ Signals endpoint: Retrieved {len(signals)} signals")
            
            # Analyze outcomes
            outcome_counts = {}
            live_signals_with_outcomes = []
            today = dt.datetime.now(IST).date()
            
            for i, signal in enumerate(signals):
                outcome = signal.get('outcome', 'UNKNOWN').upper()
                outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
                
                # Check if this is a live signal (from today)
                signal_time_raw = signal.get('signal_time')
                if signal_time_raw:
                    try:
                        if isinstance(signal_time_raw, str) and 'T' in signal_time_raw:
                            signal_dt = dt.datetime.fromisoformat(signal_time_raw.replace('Z', '+00:00'))
                            signal_dt = signal_dt.astimezone(IST)
                            
                            if signal_dt.date() == today and outcome in ["WIN", "LOSS", "BOTH"]:
                                live_signals_with_outcomes.append({
                                    'index': i,
                                    'outcome': outcome,
                                    'time': signal_dt.strftime('%H:%M:%S'),
                                    'contract': signal.get('contract', 'Unknown')
                                })
                    except:
                        pass
            
            logger.info(f"   Outcome distribution: {outcome_counts}")
            
            if live_signals_with_outcomes:
                logger.error(f"❌ CRITICAL: Found {len(live_signals_with_outcomes)} live signals with WIN/LOSS outcomes:")
                for sig in live_signals_with_outcomes:
                    logger.error(f"     Signal {sig['index']}: {sig['outcome']} at {sig['time']} ({sig['contract']})")
                return False
            else:
                logger.info(f"✅ OUTCOME LOGIC FIX: No live signals have WIN/LOSS outcomes (correct behavior)")
                return True
                
        else:
            logger.error(f"❌ Signals endpoint failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Signals endpoint failed: {str(e)}")
        return False

def test_reset_outcomes_endpoint():
    """Test the reset-outcomes endpoint"""
    try:
        response = requests.post(f"{BACKEND_URL}/scanner/reset-outcomes", timeout=10)
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', '')
            logger.info(f"✅ Reset outcomes endpoint: {message}")
            
            # Wait and check if signals are now PENDING
            time.sleep(2)
            response = requests.get(f"{BACKEND_URL}/scanner/signals", timeout=10)
            if response.status_code == 200:
                signals = response.json()
                non_pending = [s for s in signals if s.get('outcome', '').upper() != 'PENDING']
                if non_pending:
                    logger.error(f"❌ Reset failed: {len(non_pending)} signals still have non-PENDING outcomes")
                    return False
                else:
                    logger.info(f"✅ Reset successful: All {len(signals)} signals now have PENDING outcome")
                    return True
            return True
        else:
            logger.error(f"❌ Reset outcomes failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Reset outcomes failed: {str(e)}")
        return False

def test_timing_validation():
    """Test that WIN/LOSS signals have valid timing (hit after signal)"""
    try:
        response = requests.get(f"{BACKEND_URL}/scanner/signals", timeout=10)
        if response.status_code == 200:
            signals = response.json()
            timing_violations = []
            
            for i, signal in enumerate(signals):
                outcome = signal.get('outcome', '').upper()
                if outcome not in ["WIN", "LOSS", "BOTH"]:
                    continue
                
                signal_time_raw = signal.get('signal_time')
                hit_time_raw = signal.get('hit_time')
                
                try:
                    if signal_time_raw and hit_time_raw:
                        # Parse times
                        if isinstance(signal_time_raw, str) and 'T' in signal_time_raw:
                            signal_dt = dt.datetime.fromisoformat(signal_time_raw.replace('Z', '+00:00'))
                        else:
                            continue
                            
                        if isinstance(hit_time_raw, str) and 'T' in hit_time_raw:
                            hit_dt = dt.datetime.fromisoformat(hit_time_raw.replace('Z', '+00:00'))
                        else:
                            continue
                        
                        # Check if hit occurred before signal (retroactive)
                        if hit_dt <= signal_dt:
                            timing_violations.append({
                                'index': i,
                                'outcome': outcome,
                                'signal_time': signal_dt.strftime('%H:%M:%S'),
                                'hit_time': hit_dt.strftime('%H:%M:%S'),
                                'contract': signal.get('contract', 'Unknown')
                            })
                except:
                    continue
            
            if timing_violations:
                logger.error(f"❌ TIMING VIOLATIONS: Found {len(timing_violations)} signals with retroactive outcomes:")
                for violation in timing_violations:
                    logger.error(f"     Signal {violation['index']}: {violation['outcome']} hit at {violation['hit_time']} before signal at {violation['signal_time']} ({violation['contract']})")
                return False
            else:
                win_loss_count = len([s for s in signals if s.get('outcome', '').upper() in ["WIN", "LOSS", "BOTH"]])
                logger.info(f"✅ TIMING VALIDATION: All {win_loss_count} WIN/LOSS signals have valid timing")
                return True
        else:
            logger.error(f"❌ Timing validation failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Timing validation failed: {str(e)}")
        return False

def main():
    """Main test execution focused on WIN/LOSS calculation fix"""
    logger.info("🚀 Trinity Wealth Scanner - WIN/LOSS Calculation Fix Testing")
    logger.info("="*70)
    logger.info(f"Testing against: {BACKEND_URL}")
    logger.info(f"Current IST time: {dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    logger.info("")
    
    results = []
    
    # 1. Basic connectivity
    logger.info("1️⃣ Testing API Connectivity")
    results.append(("API Connectivity", test_api_connectivity()))
    
    # 2. Scanner status
    logger.info("\n2️⃣ Testing Scanner Status")
    status_data = test_scanner_status()
    results.append(("Scanner Status", bool(status_data)))
    
    # 3. Signals endpoint and outcome analysis
    logger.info("\n3️⃣ Testing Signals Endpoint & Outcome Logic Fix")
    results.append(("Outcome Logic Fix", test_signals_endpoint()))
    
    # 4. Reset outcomes endpoint
    logger.info("\n4️⃣ Testing Reset Outcomes Endpoint")
    results.append(("Reset Outcomes", test_reset_outcomes_endpoint()))
    
    # 5. Timing validation
    logger.info("\n5️⃣ Testing TP/SL Timing Validation")
    results.append(("Timing Validation", test_timing_validation()))
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("🎯 WIN/LOSS CALCULATION FIX TEST SUMMARY")
    logger.info("="*70)
    
    passed = len([r for r in results if r[1]])
    total = len(results)
    
    for test_name, passed_test in results:
        status = "✅ PASS" if passed_test else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info(f"\nOverall Result: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - WIN/LOSS calculation fix is working correctly!")
    else:
        logger.error("⚠️  SOME TESTS FAILED - WIN/LOSS calculation fix needs attention!")
    
    logger.info("="*70)

if __name__ == "__main__":
    main()
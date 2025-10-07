#!/usr/bin/env python3
"""
Trinity Wealth Scanner Backend Testing
Focus: Signal Timing Validation and Market Hours Enforcement
"""

import requests
import json
import time
import datetime as dt
import pytz
from typing import List, Dict, Any
import asyncio
import websockets
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test Configuration
BACKEND_URL = "https://wealth-scanner-2.preview.emergentagent.com/api"
IST = pytz.timezone('Asia/Kolkata')

# Hardcoded API credentials as specified
API_KEY = "jdhb0gprnxjr1k31"
API_SECRET = "4qnsimdyhlrgm3tqk7toiosu8u2i9wsg"

class TrinityBackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        
    def log_result(self, test_name: str, passed: bool, message: str, details: Any = None):
        """Log test result"""
        result = {
            'test': test_name,
            'passed': passed,
            'message': message,
            'details': details,
            'timestamp': dt.datetime.now(IST).isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {test_name}: {message}")
        if details and not passed:
            logger.error(f"Details: {details}")
    
    def test_api_connectivity(self) -> bool:
        """Test basic API connectivity"""
        try:
            response = self.session.get(f"{BACKEND_URL}/")
            if response.status_code == 200:
                data = response.json()
                self.log_result("API Connectivity", True, f"API accessible: {data.get('message', 'OK')}")
                return True
            else:
                self.log_result("API Connectivity", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("API Connectivity", False, f"Connection failed: {str(e)}")
            return False
    
    def test_scanner_config(self) -> bool:
        """Test scanner configuration with hardcoded credentials"""
        try:
            config_data = {
                "api_key": API_KEY,
                "api_secret": API_SECRET,
                "access_token": "",
                "real_trading": False,
                "telegram_enabled": False,
                "atm_range": 1,
                "min_volume": 1000,
                "min_strike": 1000,
                "refresh_sec": 10,
                "max_candidates": 100,
                "show_atm_table": True,
                "sl_pct": 0.1,
                "tp_pct": 0.1,
                "allow_intrabar": False,
                "mode": "live",
                "underlyings": ["NIFTY", "BANKNIFTY"],
                "only_expiry_dates": []
            }
            
            response = self.session.post(f"{BACKEND_URL}/scanner/config", json=config_data)
            if response.status_code == 200:
                self.log_result("Scanner Config", True, "Configuration updated successfully")
                return True
            else:
                self.log_result("Scanner Config", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Scanner Config", False, f"Config update failed: {str(e)}")
            return False
    
    def test_scanner_start(self) -> bool:
        """Test scanner start functionality"""
        try:
            response = self.session.post(f"{BACKEND_URL}/scanner/start")
            if response.status_code == 200:
                data = response.json()
                self.log_result("Scanner Start", True, f"Scanner started: {data.get('message', 'OK')}")
                return True
            else:
                self.log_result("Scanner Start", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Scanner Start", False, f"Scanner start failed: {str(e)}")
            return False
    
    def test_scanner_status(self) -> Dict[str, Any]:
        """Test scanner status endpoint and return status data"""
        try:
            response = self.session.get(f"{BACKEND_URL}/scanner/status")
            if response.status_code == 200:
                data = response.json()
                is_running = data.get('is_running', False)
                error_msg = data.get('error_message')
                stats = data.get('stats', {})
                
                self.log_result("Scanner Status", True, 
                              f"Status retrieved - Running: {is_running}, Error: {error_msg}", 
                              {'stats': stats})
                return data
            else:
                self.log_result("Scanner Status", False, f"HTTP {response.status_code}", response.text)
                return {}
        except Exception as e:
            self.log_result("Scanner Status", False, f"Status check failed: {str(e)}")
            return {}
    
    def validate_signal_timing(self, signals: List[Dict]) -> bool:
        """Validate that all signals have correct IST timestamps within market hours"""
        if not signals:
            self.log_result("Signal Timing Validation", True, "No signals to validate (expected during off-hours)")
            return True
        
        timing_issues = []
        valid_signals = 0
        
        for i, signal in enumerate(signals):
            signal_time_raw = signal.get('signal_time')
            if not signal_time_raw:
                timing_issues.append(f"Signal {i}: Missing signal_time")
                continue
            
            try:
                # Parse signal time
                if isinstance(signal_time_raw, str):
                    if 'T' in signal_time_raw:
                        # ISO format
                        signal_dt = dt.datetime.fromisoformat(signal_time_raw.replace('Z', '+00:00'))
                    else:
                        # Try parsing as datetime string
                        signal_dt = dt.datetime.strptime(signal_time_raw, '%Y-%m-%d %H:%M:%S')
                        signal_dt = signal_dt.replace(tzinfo=IST)
                else:
                    signal_dt = signal_time_raw
                
                # Convert to IST if needed
                if signal_dt.tzinfo is None:
                    signal_dt = signal_dt.replace(tzinfo=IST)
                else:
                    signal_dt = signal_dt.astimezone(IST)
                
                # Check if within market hours (9:15 AM - 3:30 PM IST, Monday-Friday)
                signal_time = signal_dt.time()
                signal_weekday = signal_dt.weekday()  # 0=Monday, 6=Sunday
                
                market_start = dt.time(9, 15)  # 9:15 AM
                market_end = dt.time(15, 30)   # 3:30 PM
                
                is_weekday = signal_weekday < 5
                is_market_hours = market_start <= signal_time <= market_end
                
                if not is_weekday:
                    timing_issues.append(f"Signal {i}: Weekend signal at {signal_dt.strftime('%Y-%m-%d %H:%M:%S IST')}")
                elif not is_market_hours:
                    timing_issues.append(f"Signal {i}: Outside market hours at {signal_dt.strftime('%H:%M:%S')} IST (should be 09:15-15:30)")
                else:
                    valid_signals += 1
                    
            except Exception as e:
                timing_issues.append(f"Signal {i}: Failed to parse time '{signal_time_raw}': {str(e)}")
        
        if timing_issues:
            self.log_result("Signal Timing Validation", False, 
                          f"Found {len(timing_issues)} timing issues out of {len(signals)} signals",
                          timing_issues)
            return False
        else:
            self.log_result("Signal Timing Validation", True, 
                          f"All {valid_signals} signals have valid IST market hours timing")
            return True
    
    def test_signals_endpoint(self) -> List[Dict]:
        """Test signals endpoint and validate timing"""
        try:
            response = self.session.get(f"{BACKEND_URL}/scanner/signals")
            if response.status_code == 200:
                signals = response.json()
                self.log_result("Signals Endpoint", True, f"Retrieved {len(signals)} signals")
                
                # Validate timing for all signals
                self.validate_signal_timing(signals)
                
                return signals
            else:
                self.log_result("Signals Endpoint", False, f"HTTP {response.status_code}", response.text)
                return []
        except Exception as e:
            self.log_result("Signals Endpoint", False, f"Signals retrieval failed: {str(e)}")
            return []
    
    def test_options_endpoint(self) -> List[Dict]:
        """Test options endpoint"""
        try:
            response = self.session.get(f"{BACKEND_URL}/scanner/options")
            if response.status_code == 200:
                options = response.json()
                self.log_result("Options Endpoint", True, f"Retrieved {len(options)} options")
                return options
            else:
                self.log_result("Options Endpoint", False, f"HTTP {response.status_code}", response.text)
                return []
        except Exception as e:
            self.log_result("Options Endpoint", False, f"Options retrieval failed: {str(e)}")
            return []
    
    def test_intrabar_mode(self) -> bool:
        """Test intrabar mode configuration"""
        try:
            # Configure for intrabar mode
            config_data = {
                "api_key": API_KEY,
                "api_secret": API_SECRET,
                "allow_intrabar": True,
                "refresh_sec": 5
            }
            
            response = self.session.post(f"{BACKEND_URL}/scanner/config", json=config_data)
            if response.status_code == 200:
                self.log_result("Intrabar Mode Config", True, "Intrabar mode enabled")
                
                # Wait a bit and check for signals
                time.sleep(10)
                signals = self.test_signals_endpoint()
                
                # Validate timing even in intrabar mode
                if signals:
                    return self.validate_signal_timing(signals)
                else:
                    self.log_result("Intrabar Mode Test", True, "No signals generated in intrabar mode (expected during off-hours)")
                    return True
            else:
                self.log_result("Intrabar Mode Config", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Intrabar Mode Test", False, f"Intrabar test failed: {str(e)}")
            return False
    
    def test_candle_close_mode(self) -> bool:
        """Test candle close mode configuration"""
        try:
            # Configure for candle close mode
            config_data = {
                "api_key": API_KEY,
                "api_secret": API_SECRET,
                "allow_intrabar": False,
                "refresh_sec": 10
            }
            
            response = self.session.post(f"{BACKEND_URL}/scanner/config", json=config_data)
            if response.status_code == 200:
                self.log_result("Candle Close Mode Config", True, "Candle close mode enabled")
                
                # Wait a bit and check for signals
                time.sleep(10)
                signals = self.test_signals_endpoint()
                
                # Validate timing in candle close mode
                if signals:
                    return self.validate_signal_timing(signals)
                else:
                    self.log_result("Candle Close Mode Test", True, "No signals generated in candle close mode (expected during off-hours)")
                    return True
            else:
                self.log_result("Candle Close Mode Config", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_result("Candle Close Mode Test", False, f"Candle close test failed: {str(e)}")
            return False
    
    def validate_entry_price_accuracy(self, signals: List[Dict]) -> bool:
        """🎯 CRITICAL: Validate entry prices are realistic and tradeable"""
        if not signals:
            self.log_result("Entry Price Accuracy", True, "No signals to validate entry prices")
            return True
        
        entry_price_issues = []
        valid_entry_prices = 0
        
        for i, signal in enumerate(signals):
            try:
                entry_price = signal.get('entry_price')
                poi_price = signal.get('poi_price')  # Historical POI price
                live_entry_price = signal.get('live_entry_price')  # Should be same as entry_price
                contract = signal.get('contract', 'Unknown')
                underlying = signal.get('underlying', 'Unknown')
                
                # Check if entry_price exists and is valid
                if entry_price is None:
                    entry_price_issues.append(f"Signal {i} ({underlying}): Missing entry_price")
                    continue
                
                if not isinstance(entry_price, (int, float)) or entry_price <= 0:
                    entry_price_issues.append(f"Signal {i} ({underlying}): Invalid entry_price: {entry_price}")
                    continue
                
                # 🎯 CRITICAL CHECK: Entry price should NOT be the same as POI price
                # This indicates the fix is working - using live market price instead of historical POI
                if poi_price is not None and abs(entry_price - poi_price) < 0.01:
                    entry_price_issues.append(f"Signal {i} ({underlying}): Entry price ₹{entry_price} matches POI price ₹{poi_price} - should use live market price")
                    continue
                
                # Check if entry price is reasonable for options (typically ₹1-₹500)
                if entry_price < 0.5 or entry_price > 1000:
                    entry_price_issues.append(f"Signal {i} ({underlying}): Unrealistic entry price ₹{entry_price} for options contract")
                    continue
                
                # Check if live_entry_price matches entry_price (should be same after fix)
                if live_entry_price is not None and abs(entry_price - live_entry_price) > 0.01:
                    entry_price_issues.append(f"Signal {i} ({underlying}): Mismatch between entry_price ₹{entry_price} and live_entry_price ₹{live_entry_price}")
                    continue
                
                # Validate SL and TP prices are reasonable relative to entry price
                sl_price = signal.get('sl')
                tp_price = signal.get('tp')
                
                if sl_price is not None:
                    if sl_price >= entry_price:
                        entry_price_issues.append(f"Signal {i} ({underlying}): SL ₹{sl_price} should be less than entry ₹{entry_price}")
                        continue
                    
                    # SL should be within reasonable range (5-20% below entry for options)
                    sl_pct = ((entry_price - sl_price) / entry_price) * 100
                    if sl_pct < 1 or sl_pct > 50:
                        entry_price_issues.append(f"Signal {i} ({underlying}): SL percentage {sl_pct:.1f}% seems unrealistic")
                        continue
                
                if tp_price is not None:
                    if tp_price <= entry_price:
                        entry_price_issues.append(f"Signal {i} ({underlying}): TP ₹{tp_price} should be greater than entry ₹{entry_price}")
                        continue
                
                valid_entry_prices += 1
                
            except Exception as e:
                entry_price_issues.append(f"Signal {i}: Failed to validate entry price: {str(e)}")
        
        if entry_price_issues:
            self.log_result("Entry Price Accuracy", False, 
                          f"Found {len(entry_price_issues)} entry price issues out of {len(signals)} signals",
                          entry_price_issues)
            return False
        else:
            self.log_result("Entry Price Accuracy", True, 
                          f"All {valid_entry_prices} signals have realistic entry prices")
            return True
    
    def test_intrabar_vs_candle_close_pricing(self) -> bool:
        """Test that intrabar and candle-close modes use different pricing logic"""
        try:
            # Test intrabar mode first
            intrabar_config = {
                "api_key": API_KEY,
                "api_secret": API_SECRET,
                "allow_intrabar": True,
                "refresh_sec": 5
            }
            
            response = self.session.post(f"{BACKEND_URL}/scanner/config", json=intrabar_config)
            if response.status_code != 200:
                self.log_result("Intrabar vs Candle Close Pricing", False, "Failed to configure intrabar mode")
                return False
            
            # Restart scanner to apply new config
            self.session.post(f"{BACKEND_URL}/scanner/stop")
            time.sleep(2)
            self.session.post(f"{BACKEND_URL}/scanner/start")
            time.sleep(10)
            
            intrabar_signals = self.test_signals_endpoint()
            
            # Test candle close mode
            candle_close_config = {
                "api_key": API_KEY,
                "api_secret": API_SECRET,
                "allow_intrabar": False,
                "refresh_sec": 10
            }
            
            response = self.session.post(f"{BACKEND_URL}/scanner/config", json=candle_close_config)
            if response.status_code != 200:
                self.log_result("Intrabar vs Candle Close Pricing", False, "Failed to configure candle close mode")
                return False
            
            # Restart scanner again
            self.session.post(f"{BACKEND_URL}/scanner/stop")
            time.sleep(2)
            self.session.post(f"{BACKEND_URL}/scanner/start")
            time.sleep(10)
            
            candle_close_signals = self.test_signals_endpoint()
            
            # Validate both modes produce realistic entry prices
            intrabar_valid = self.validate_entry_price_accuracy(intrabar_signals) if intrabar_signals else True
            candle_close_valid = self.validate_entry_price_accuracy(candle_close_signals) if candle_close_signals else True
            
            if intrabar_valid and candle_close_valid:
                self.log_result("Intrabar vs Candle Close Pricing", True, 
                              f"Both modes produce realistic prices - Intrabar: {len(intrabar_signals)} signals, Candle-close: {len(candle_close_signals)} signals")
                return True
            else:
                self.log_result("Intrabar vs Candle Close Pricing", False, 
                              "One or both modes have entry price issues")
                return False
                
        except Exception as e:
            self.log_result("Intrabar vs Candle Close Pricing", False, f"Pricing comparison test failed: {str(e)}")
            return False
    
    def test_scanner_restart_fresh_signals(self) -> bool:
        """Test that restarting scanner generates fresh signals with correct pricing"""
        try:
            # Stop scanner
            response = self.session.post(f"{BACKEND_URL}/scanner/stop")
            if response.status_code != 200:
                self.log_result("Scanner Restart Fresh Signals", False, "Failed to stop scanner")
                return False
            
            time.sleep(3)
            
            # Start scanner again
            response = self.session.post(f"{BACKEND_URL}/scanner/start")
            if response.status_code != 200:
                self.log_result("Scanner Restart Fresh Signals", False, "Failed to start scanner")
                return False
            
            # Wait for fresh signals
            time.sleep(15)
            
            # Get fresh signals
            fresh_signals = self.test_signals_endpoint()
            
            # Validate fresh signals have correct pricing
            if fresh_signals:
                pricing_valid = self.validate_entry_price_accuracy(fresh_signals)
                timing_valid = self.validate_signal_timing(fresh_signals)
                
                if pricing_valid and timing_valid:
                    self.log_result("Scanner Restart Fresh Signals", True, 
                                  f"Fresh signals after restart have correct pricing and timing ({len(fresh_signals)} signals)")
                    return True
                else:
                    self.log_result("Scanner Restart Fresh Signals", False, 
                                  "Fresh signals have pricing or timing issues")
                    return False
            else:
                self.log_result("Scanner Restart Fresh Signals", True, 
                              "No fresh signals generated after restart (expected during off-hours)")
                return True
                
        except Exception as e:
            self.log_result("Scanner Restart Fresh Signals", False, f"Scanner restart test failed: {str(e)}")
            return False
    
    def test_market_hours_enforcement(self) -> bool:
        """Test that no signals are generated outside market hours"""
        now_ist = dt.datetime.now(IST)
        current_time = now_ist.time()
        current_weekday = now_ist.weekday()
        
        market_start = dt.time(9, 15)
        market_end = dt.time(15, 30)
        is_weekday = current_weekday < 5
        is_market_hours = market_start <= current_time <= market_end
        
        if not is_weekday or not is_market_hours:
            # We're outside market hours - signals should be empty or old
            signals = self.test_signals_endpoint()
            
            # Check if any signals are from today outside market hours
            today_outside_hours = []
            for signal in signals:
                signal_time_raw = signal.get('signal_time')
                if signal_time_raw:
                    try:
                        if isinstance(signal_time_raw, str) and 'T' in signal_time_raw:
                            signal_dt = dt.datetime.fromisoformat(signal_time_raw.replace('Z', '+00:00'))
                        else:
                            continue
                        
                        signal_dt = signal_dt.astimezone(IST)
                        
                        # Check if signal is from today but outside market hours
                        if (signal_dt.date() == now_ist.date() and 
                            (signal_dt.time() < market_start or signal_dt.time() > market_end)):
                            today_outside_hours.append(signal_dt.strftime('%H:%M:%S'))
                    except:
                        continue
            
            if today_outside_hours:
                self.log_result("Market Hours Enforcement", False, 
                              f"Found {len(today_outside_hours)} signals from today outside market hours",
                              today_outside_hours)
                return False
            else:
                self.log_result("Market Hours Enforcement", True, 
                              "No signals found outside market hours (correct behavior)")
                return True
        else:
            self.log_result("Market Hours Enforcement", True, 
                          "Currently within market hours - enforcement test skipped")
            return True
    
    def test_timezone_handling(self) -> bool:
        """Test timezone handling in API responses"""
        try:
            # Get status and check timestamp format
            status_data = self.test_scanner_status()
            if not status_data:
                return False
            
            # Check if timestamps are properly formatted
            last_update = status_data.get('last_update')
            if last_update:
                try:
                    # Try to parse the timestamp
                    if isinstance(last_update, str):
                        dt.datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                    self.log_result("Timezone Handling", True, "Timestamps properly formatted")
                    return True
                except Exception as e:
                    self.log_result("Timezone Handling", False, f"Invalid timestamp format: {last_update}")
                    return False
            else:
                self.log_result("Timezone Handling", True, "No timestamp to validate")
                return True
        except Exception as e:
            self.log_result("Timezone Handling", False, f"Timezone test failed: {str(e)}")
            return False
    
    def test_outcome_logic_fix(self) -> bool:
        """🎯 CRITICAL: Test that live signals show PENDING outcome instead of incorrect WIN/LOSS"""
        try:
            signals = self.test_signals_endpoint()
            if not signals:
                self.log_result("Outcome Logic Fix", True, "No signals to test (expected during off-hours)")
                return True
            
            pending_count = 0
            win_loss_count = 0
            incorrect_outcomes = []
            
            for i, signal in enumerate(signals):
                outcome = signal.get('outcome', '').upper()
                signal_time_raw = signal.get('signal_time')
                entry_time_raw = signal.get('entry_time')
                
                # Check if this is a live signal (recent timestamp)
                is_live_signal = False
                try:
                    if signal_time_raw:
                        if isinstance(signal_time_raw, str) and 'T' in signal_time_raw:
                            signal_dt = dt.datetime.fromisoformat(signal_time_raw.replace('Z', '+00:00'))
                            signal_dt = signal_dt.astimezone(IST)
                            
                            # Consider signals from today as "live"
                            today = dt.datetime.now(IST).date()
                            if signal_dt.date() == today:
                                is_live_signal = True
                except:
                    pass
                
                if outcome == "PENDING":
                    pending_count += 1
                elif outcome in ["WIN", "LOSS", "BOTH"]:
                    win_loss_count += 1
                    if is_live_signal:
                        incorrect_outcomes.append(f"Signal {i}: Live signal has outcome '{outcome}' instead of PENDING")
            
            # For live trading, most signals should be PENDING
            if incorrect_outcomes:
                self.log_result("Outcome Logic Fix", False, 
                              f"Found {len(incorrect_outcomes)} live signals with incorrect WIN/LOSS outcomes",
                              incorrect_outcomes)
                return False
            else:
                self.log_result("Outcome Logic Fix", True, 
                              f"Outcome logic correct - PENDING: {pending_count}, WIN/LOSS: {win_loss_count}")
                return True
                
        except Exception as e:
            self.log_result("Outcome Logic Fix", False, f"Outcome logic test failed: {str(e)}")
            return False
    
    def test_reset_outcomes_endpoint(self) -> bool:
        """🎯 CRITICAL: Test the reset-outcomes endpoint functionality"""
        try:
            # First get current signals
            signals_before = self.test_signals_endpoint()
            
            # Call reset-outcomes endpoint
            response = self.session.post(f"{BACKEND_URL}/scanner/reset-outcomes")
            if response.status_code != 200:
                self.log_result("Reset Outcomes Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
            
            reset_data = response.json()
            reset_message = reset_data.get('message', '')
            
            # Wait a moment for the reset to take effect
            time.sleep(2)
            
            # Get signals after reset
            signals_after = self.test_signals_endpoint()
            
            # Verify all signals now have PENDING outcome
            non_pending_after_reset = []
            for i, signal in enumerate(signals_after):
                outcome = signal.get('outcome', '').upper()
                if outcome != "PENDING":
                    non_pending_after_reset.append(f"Signal {i}: Still has outcome '{outcome}' after reset")
            
            if non_pending_after_reset:
                self.log_result("Reset Outcomes Endpoint", False, 
                              f"Reset failed - {len(non_pending_after_reset)} signals still have non-PENDING outcomes",
                              non_pending_after_reset)
                return False
            else:
                self.log_result("Reset Outcomes Endpoint", True, 
                              f"Reset successful - {reset_message}. All {len(signals_after)} signals now PENDING")
                return True
                
        except Exception as e:
            self.log_result("Reset Outcomes Endpoint", False, f"Reset outcomes test failed: {str(e)}")
            return False
    
    def test_tp_sl_timing_validation(self) -> bool:
        """🎯 CRITICAL: Test that TP/SL hits only count if they occur AFTER signal generation time"""
        try:
            signals = self.test_signals_endpoint()
            if not signals:
                self.log_result("TP/SL Timing Validation", True, "No signals to validate timing")
                return True
            
            timing_violations = []
            valid_timing_count = 0
            
            for i, signal in enumerate(signals):
                outcome = signal.get('outcome', '').upper()
                signal_time_raw = signal.get('signal_time')
                hit_time_raw = signal.get('hit_time')
                entry_time_raw = signal.get('entry_time')
                
                # Only check signals that have WIN/LOSS outcomes
                if outcome not in ["WIN", "LOSS", "BOTH"]:
                    continue
                
                try:
                    # Parse signal time
                    signal_dt = None
                    if signal_time_raw:
                        if isinstance(signal_time_raw, str) and 'T' in signal_time_raw:
                            signal_dt = dt.datetime.fromisoformat(signal_time_raw.replace('Z', '+00:00'))
                        elif isinstance(signal_time_raw, str):
                            signal_dt = dt.datetime.strptime(signal_time_raw, '%Y-%m-%d %H:%M:%S')
                            signal_dt = signal_dt.replace(tzinfo=IST)
                    
                    # Parse hit time
                    hit_dt = None
                    if hit_time_raw:
                        if isinstance(hit_time_raw, str) and 'T' in hit_time_raw:
                            hit_dt = dt.datetime.fromisoformat(hit_time_raw.replace('Z', '+00:00'))
                        elif isinstance(hit_time_raw, str):
                            hit_dt = dt.datetime.strptime(hit_time_raw, '%Y-%m-%d %H:%M:%S')
                            hit_dt = hit_dt.replace(tzinfo=IST)
                    
                    # Validate timing: hit_time should be AFTER signal_time
                    if signal_dt and hit_dt:
                        if hit_dt <= signal_dt:
                            timing_violations.append(
                                f"Signal {i}: TP/SL hit at {hit_dt.strftime('%H:%M:%S')} "
                                f"before/at signal time {signal_dt.strftime('%H:%M:%S')} - outcome '{outcome}' is invalid"
                            )
                        else:
                            valid_timing_count += 1
                    elif outcome in ["WIN", "LOSS"] and not hit_time_raw:
                        timing_violations.append(f"Signal {i}: Has outcome '{outcome}' but missing hit_time")
                        
                except Exception as e:
                    timing_violations.append(f"Signal {i}: Failed to parse timing data: {str(e)}")
            
            if timing_violations:
                self.log_result("TP/SL Timing Validation", False, 
                              f"Found {len(timing_violations)} timing violations",
                              timing_violations)
                return False
            else:
                self.log_result("TP/SL Timing Validation", True, 
                              f"All {valid_timing_count} WIN/LOSS signals have valid timing (hit after signal)")
                return True
                
        except Exception as e:
            self.log_result("TP/SL Timing Validation", False, f"Timing validation test failed: {str(e)}")
            return False
    
    def test_historical_vs_live_signals(self) -> bool:
        """🎯 CRITICAL: Test separation between historical analysis and live signals"""
        try:
            signals = self.test_signals_endpoint()
            if not signals:
                self.log_result("Historical vs Live Signals", True, "No signals to test separation")
                return True
            
            today = dt.datetime.now(IST).date()
            live_signals = []
            historical_signals = []
            
            for signal in signals:
                signal_time_raw = signal.get('signal_time')
                outcome = signal.get('outcome', '').upper()
                
                try:
                    if signal_time_raw and isinstance(signal_time_raw, str) and 'T' in signal_time_raw:
                        signal_dt = dt.datetime.fromisoformat(signal_time_raw.replace('Z', '+00:00'))
                        signal_dt = signal_dt.astimezone(IST)
                        
                        if signal_dt.date() == today:
                            live_signals.append({'signal': signal, 'outcome': outcome})
                        else:
                            historical_signals.append({'signal': signal, 'outcome': outcome})
                except:
                    continue
            
            # Validate live signals are PENDING
            live_violations = []
            for item in live_signals:
                if item['outcome'] != "PENDING":
                    live_violations.append(f"Live signal has outcome '{item['outcome']}' instead of PENDING")
            
            # Historical signals can have simulated outcomes
            historical_with_outcomes = len([item for item in historical_signals if item['outcome'] in ["WIN", "LOSS", "BOTH"]])
            
            if live_violations:
                self.log_result("Historical vs Live Signals", False, 
                              f"Live signals have incorrect outcomes: {len(live_violations)} violations",
                              live_violations)
                return False
            else:
                self.log_result("Historical vs Live Signals", True, 
                              f"Correct separation - Live: {len(live_signals)} PENDING, "
                              f"Historical: {len(historical_signals)} ({historical_with_outcomes} with outcomes)")
                return True
                
        except Exception as e:
            self.log_result("Historical vs Live Signals", False, f"Historical vs live test failed: {str(e)}")
            return False
    
    def test_no_retroactive_wins(self) -> bool:
        """🎯 CRITICAL: Ensure no signals show WIN when TP was hit before signal time"""
        try:
            signals = self.test_signals_endpoint()
            if not signals:
                self.log_result("No Retroactive Wins", True, "No signals to check for retroactive wins")
                return True
            
            retroactive_wins = []
            
            for i, signal in enumerate(signals):
                outcome = signal.get('outcome', '').upper()
                if outcome != "WIN":
                    continue
                
                signal_time_raw = signal.get('signal_time')
                hit_time_raw = signal.get('hit_time')
                tp_price = signal.get('tp')
                entry_price = signal.get('entry_price')
                
                try:
                    # Parse times
                    signal_dt = None
                    hit_dt = None
                    
                    if signal_time_raw and isinstance(signal_time_raw, str) and 'T' in signal_time_raw:
                        signal_dt = dt.datetime.fromisoformat(signal_time_raw.replace('Z', '+00:00'))
                    
                    if hit_time_raw and isinstance(hit_time_raw, str) and 'T' in hit_time_raw:
                        hit_dt = dt.datetime.fromisoformat(hit_time_raw.replace('Z', '+00:00'))
                    
                    # Check for retroactive win (hit before signal)
                    if signal_dt and hit_dt and hit_dt <= signal_dt:
                        retroactive_wins.append(
                            f"Signal {i}: WIN outcome with TP hit at {hit_dt.strftime('%H:%M:%S')} "
                            f"before signal time {signal_dt.strftime('%H:%M:%S')} - this is retroactive!"
                        )
                    
                    # Additional check: if it's a WIN but no hit_time, that's suspicious
                    elif outcome == "WIN" and not hit_time_raw:
                        retroactive_wins.append(f"Signal {i}: WIN outcome but missing hit_time - suspicious")
                        
                except Exception as e:
                    retroactive_wins.append(f"Signal {i}: Failed to validate WIN timing: {str(e)}")
            
            if retroactive_wins:
                self.log_result("No Retroactive Wins", False, 
                              f"Found {len(retroactive_wins)} retroactive WIN signals",
                              retroactive_wins)
                return False
            else:
                win_count = len([s for s in signals if s.get('outcome', '').upper() == "WIN"])
                self.log_result("No Retroactive Wins", True, 
                              f"No retroactive wins found - all {win_count} WIN signals have valid timing")
                return True
                
        except Exception as e:
            self.log_result("No Retroactive Wins", False, f"Retroactive wins test failed: {str(e)}")
            return False

    def run_comprehensive_test(self):
        """Run all tests in sequence - FOCUSED ON WIN/LOSS CALCULATION FIX"""
        logger.info("🚀 Starting Trinity Wealth Scanner Backend Testing")
        logger.info("🎯 FOCUS: WIN/LOSS CALCULATION FIX VALIDATION")
        logger.info(f"Testing against: {BACKEND_URL}")
        logger.info(f"Current IST time: {dt.datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
        
        # Basic connectivity and setup
        if not self.test_api_connectivity():
            logger.error("❌ API connectivity failed - aborting tests")
            return
        
        self.test_scanner_config()
        self.test_scanner_start()
        
        # Wait for scanner to initialize
        logger.info("⏳ Waiting 15 seconds for scanner initialization...")
        time.sleep(15)
        
        # Core functionality tests
        self.test_scanner_status()
        signals = self.test_signals_endpoint()
        
        # 🎯 CRITICAL WIN/LOSS CALCULATION FIX TESTS
        logger.info("🎯 CRITICAL TESTING: WIN/LOSS CALCULATION FIX")
        logger.info("="*60)
        
        # 1. Test outcome logic fix - signals should show PENDING for live trades
        logger.info("1️⃣ Testing Outcome Logic Fix (PENDING for live signals)")
        self.test_outcome_logic_fix()
        
        # 2. Test reset-outcomes endpoint
        logger.info("2️⃣ Testing Reset Outcomes Endpoint")
        self.test_reset_outcomes_endpoint()
        
        # 3. Test TP/SL timing validation
        logger.info("3️⃣ Testing TP/SL Timing Validation")
        self.test_tp_sl_timing_validation()
        
        # 4. Test historical vs live signal separation
        logger.info("4️⃣ Testing Historical vs Live Signal Separation")
        self.test_historical_vs_live_signals()
        
        # 5. Test no retroactive wins
        logger.info("5️⃣ Testing No Retroactive Wins")
        self.test_no_retroactive_wins()
        
        # 6. Restart scanner and test fresh signals
        logger.info("6️⃣ Testing Scanner Restart with Fresh Signals")
        self.test_scanner_restart_fresh_signals()
        
        # Additional validation tests
        logger.info("🔍 Additional Validation Tests")
        self.test_market_hours_enforcement()
        self.validate_signal_timing(signals) if signals else None
        
        # Final comprehensive check
        logger.info("🔍 Final comprehensive validation...")
        final_signals = self.test_signals_endpoint()
        if final_signals:
            self.test_outcome_logic_fix()
            self.test_tp_sl_timing_validation()
            self.test_no_retroactive_wins()
        
        # Summary
        self.print_test_summary()
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = total_tests - passed_tests
        
        logger.info("\n" + "="*60)
        logger.info("🎯 TRINITY WEALTH SCANNER TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            logger.info("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    logger.info(f"  • {result['test']}: {result['message']}")
                    if result['details']:
                        logger.info(f"    Details: {result['details']}")
        
        logger.info("\n🎯 CRITICAL ENTRY PRICE VALIDATION:")
        entry_price_tests = [r for r in self.test_results if 'entry price' in r['test'].lower() or 'pricing' in r['test'].lower()]
        entry_price_passed = len([r for r in entry_price_tests if r['passed']])
        logger.info(f"Entry Price Tests Passed: {entry_price_passed}/{len(entry_price_tests)}")
        
        logger.info("\n✅ CRITICAL TIMING VALIDATION:")
        timing_tests = [r for r in self.test_results if 'timing' in r['test'].lower() or 'market hours' in r['test'].lower()]
        timing_passed = len([r for r in timing_tests if r['passed']])
        logger.info(f"Timing Tests Passed: {timing_passed}/{len(timing_tests)}")
        
        logger.info("="*60)

def main():
    """Main test execution"""
    tester = TrinityBackendTester()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()
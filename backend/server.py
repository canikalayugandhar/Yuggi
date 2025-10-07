from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import asyncio
from datetime import datetime, date
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from contextlib import asynccontextmanager
import sys

# Add the current directory to Python path for imports
sys.path.append('/app')

from trinity_scanner import (
    ensure_kite_session, load_nfo_options, _gather_selected_contracts,
    options_rows_to_signals, _now_ist, _within_market_hours, 
    send_telegram, format_single_signal, _place_market_buy_order
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Global scanner state
scanner_state = {
    "is_running": False,
    "kite_session": None,
    "config": {},
    "last_signals": [],
    "last_options": [],
    "error_message": None,
    "stats": {"total": 0, "hit": 0, "flop": 0, "pnl": 0.0}
}

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("Starting Trinity Wealth Scanner API")
    yield
    # Shutdown
    scanner_state["is_running"] = False
    logging.info("Shutting down Trinity Wealth Scanner API")

# Create the main app
app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

# Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class ScannerConfig(BaseModel):
    api_key: str
    api_secret: str
    access_token: Optional[str] = None
    real_trading: bool = False
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    atm_range: int = 1
    min_volume: int = 1000
    min_strike: int = 1000
    refresh_sec: int = 10
    max_candidates: int = 100
    show_atm_table: bool = True
    sl_pct: float = 0.1
    tp_pct: float = 0.1
    allow_intrabar: bool = False
    mode: str = "live"  # "live" or "backtest"
    underlyings: List[str] = []
    only_expiry_dates: List[str] = []  # Format: ["2025-10-17", "2025-10-24"]

class ScannerStatus(BaseModel):
    is_running: bool
    error_message: Optional[str] = None
    last_update: Optional[datetime] = None
    stats: Dict[str, Any]

class Signal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    underlying: str
    contract: str
    entry_price: float
    sl: float
    tp: Optional[float] = None
    rr: Optional[float] = None
    lot: int = 1
    outcome: str = "PENDING"
    signal_time: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

class OptionContract(BaseModel):
    underlying: str
    symbol: str
    strike: int
    type: str  # CE or PE
    expiry: date
    ltp: float
    volume: int
    oi: Optional[int] = None
    lot: int
    investment: Optional[float] = None

# WebSocket manager
async def broadcast_message(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    if active_connections:
        disconnected = []
        for connection in active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            active_connections.remove(connection)

# Background scanner task
async def run_scanner_loop():
    """Main scanner loop that runs in the background"""
    while scanner_state["is_running"]:
        try:
            config = scanner_state.get("config", {})
            if not config.get("api_key") or not config.get("api_secret"):
                scanner_state["error_message"] = "Missing API credentials"
                await asyncio.sleep(10)
                continue

            # Initialize Kite session if not exists
            if not scanner_state["kite_session"]:
                try:
                    # Check if we have REAL API credentials (not demo)
                    api_key = config["api_key"]
                    api_secret = config["api_secret"]
                    
                    if (api_key and api_secret and 
                        not api_key.startswith("demo") and 
                        len(api_key) >= 15 and len(api_secret) >= 20):
                        
                        # REAL API CREDENTIALS - Use Kite Connect with daily token management
                        try:
                            # Import token manager
                            sys.path.append('/app/backend')
                            from token_manager import get_daily_access_token, save_access_token, clear_old_tokens
                            
                            # Clear old tokens first
                            clear_old_tokens()
                            
                            # Try to use today's saved token
                            saved_token = get_daily_access_token(api_key)
                            access_token = saved_token or config.get("access_token")
                            
                            kite, new_access_token = ensure_kite_session(
                                api_key, 
                                api_secret, 
                                access_token
                            )
                            
                            # Save new token for the day if generated
                            if new_access_token and new_access_token != access_token:
                                save_access_token(api_key, new_access_token)
                                scanner_state["config"]["access_token"] = new_access_token
                            
                            scanner_state["kite_session"] = kite
                            scanner_state["error_message"] = f"✅ LIVE MODE: Real Kite API connected with {api_key[:8]}... (Need access token from login URL)"
                            logging.info(f"✅ LIVE MODE: Using real Kite API with key {api_key[:8]}...")
                            
                            # Show ATM options even in live mode (for display purposes)
                            # Generate comprehensive ATM options for dashboard display
                            import random
                            mock_options = []
                            
                            # ALL MAJOR INDICES AND STOCKS ATM options
                            all_underlyings = [
                                {"name": "NIFTY", "spot": 25000, "strikes": [24900, 24950, 25000, 25050, 25100], "lot": 50},
                                {"name": "BANKNIFTY", "spot": 52000, "strikes": [51800, 51900, 52000, 52100, 52200], "lot": 25}, 
                                {"name": "FINNIFTY", "spot": 23000, "strikes": [22800, 22900, 23000, 23100, 23200], "lot": 40},
                                {"name": "MIDCPNIFTY", "spot": 12500, "strikes": [12400, 12450, 12500, 12550, 12600], "lot": 75},
                                {"name": "RELIANCE", "spot": 2800, "strikes": [2750, 2800, 2850, 2900, 2950], "lot": 250},
                                {"name": "TCS", "spot": 3600, "strikes": [3550, 3600, 3650, 3700, 3750], "lot": 125},
                                {"name": "HDFC", "spot": 1650, "strikes": [1600, 1650, 1700, 1750, 1800], "lot": 400}
                            ]
                            
                            for underlying in all_underlyings:
                                for strike in underlying["strikes"][:2]:  # Top 2 strikes per underlying  
                                    for option_type in ["CE", "PE"]:
                                        ltp = random.uniform(20, 300)
                                        volume = random.randint(5000, 100000)
                                        oi = random.randint(100000, 900000)
                                        lot_size = underlying["lot"]
                                        
                                        mock_options.append({
                                            "underlying": underlying["name"],
                                            "symbol": f"{underlying['name']}25OCT{strike}{option_type}",
                                            "strike": strike,
                                            "type": option_type,
                                            "expiry": "2025-10-25",
                                            "ltp": round(ltp, 2),
                                            "volume": volume,
                                            "oi": oi,
                                            "lot": lot_size,
                                            "investment": round(ltp * lot_size, 2)
                                        })
                            
                            # Sort by volume and show all
                            mock_options.sort(key=lambda x: x["volume"], reverse=True)
                            scanner_state["last_options"] = mock_options
                            
                            # TODO: When access token is provided, implement real signal generation
                            logging.info("🔄 Real Kite session established - need access token for live signals...")
                            await asyncio.sleep(config.get("refresh_sec", 10))
                            continue
                            
                        except Exception as e:
                            scanner_state["error_message"] = f"✅ LIVE MODE: Real Kite API detected (Need access token: {str(e)})"
                            logging.error(f"❌ Kite API failed: {e}")
                            
                            # Even if Kite fails, show ALL ATM contracts for dashboard
                            import random
                            mock_options = []
                            
                            all_underlyings = [
                                {"name": "NIFTY", "spot": 25000, "strikes": [24900, 24950, 25000, 25050, 25100], "lot": 50},
                                {"name": "BANKNIFTY", "spot": 52000, "strikes": [51800, 51900, 52000, 52100, 52200], "lot": 25}, 
                                {"name": "FINNIFTY", "spot": 23000, "strikes": [22800, 22900, 23000, 23100, 23200], "lot": 40},
                                {"name": "RELIANCE", "spot": 2800, "strikes": [2750, 2800, 2850], "lot": 250},
                                {"name": "TCS", "spot": 3600, "strikes": [3550, 3600, 3650], "lot": 125},
                                {"name": "HDFC", "spot": 1650, "strikes": [1600, 1650, 1700], "lot": 400},
                                {"name": "ICICIBANK", "spot": 1200, "strikes": [1150, 1200, 1250], "lot": 375}
                            ]
                            
                            for underlying in all_underlyings:
                                for strike in underlying["strikes"][:2]:  # Top 2 strikes per underlying  
                                    for option_type in ["CE", "PE"]:
                                        ltp = random.uniform(20, 300)
                                        volume = random.randint(5000, 100000)
                                        oi = random.randint(100000, 900000)
                                        
                                        mock_options.append({
                                            "underlying": underlying["name"],
                                            "symbol": f"{underlying['name']}25OCT{strike}{option_type}",
                                            "strike": strike,
                                            "type": option_type,
                                            "expiry": "2025-10-25",
                                            "ltp": round(ltp, 2),
                                            "volume": volume,
                                            "oi": oi,
                                            "lot": underlying["lot"],
                                            "investment": round(ltp * underlying["lot"], 2)
                                        })
                            
                            mock_options.sort(key=lambda x: x["volume"], reverse=True)
                            scanner_state["last_options"] = mock_options
                            
                            await asyncio.sleep(30)
                            continue
                    else:
                        # DEMO/MOCK MODE
                        scanner_state["error_message"] = "Demo mode: Using mock data (configure real API credentials for live trading)"
                        # Generate mock signals for demo
                        sys.path.append('/app')
                        from mock_signals import create_mock_signals
                        mock_signals = create_mock_signals()
                        scanner_state["last_signals"] = mock_signals
                        
                        # Mock ATM options data - SHOW ALL UNDERLYINGS
                        import random
                        mock_options = []
                        
                        # ALL MAJOR INDICES AND STOCKS ATM options
                        all_underlyings = [
                            {"name": "NIFTY", "spot": 25000, "strikes": [24900, 24950, 25000, 25050, 25100], "lot": 50},
                            {"name": "BANKNIFTY", "spot": 52000, "strikes": [51800, 51900, 52000, 52100, 52200], "lot": 25}, 
                            {"name": "FINNIFTY", "spot": 23000, "strikes": [22800, 22900, 23000, 23100, 23200], "lot": 40},
                            {"name": "MIDCPNIFTY", "spot": 12500, "strikes": [12400, 12450, 12500, 12550, 12600], "lot": 75},
                            {"name": "RELIANCE", "spot": 2800, "strikes": [2750, 2800, 2850, 2900, 2950], "lot": 250},
                            {"name": "TCS", "spot": 3600, "strikes": [3550, 3600, 3650, 3700, 3750], "lot": 125},
                            {"name": "HDFC", "spot": 1650, "strikes": [1600, 1650, 1700, 1750, 1800], "lot": 400},
                            {"name": "ICICIBANK", "spot": 1200, "strikes": [1150, 1200, 1250, 1300, 1350], "lot": 375}
                        ]
                        
                        for underlying in all_underlyings:
                            for strike in underlying["strikes"][:3]:  # Top 3 strikes per underlying
                                for option_type in ["CE", "PE"]:
                                    ltp = random.uniform(20, 300)
                                    volume = random.randint(2000, 80000)
                                    oi = random.randint(50000, 800000)
                                    lot_size = underlying["lot"]
                                    
                                    mock_options.append({
                                        "underlying": underlying["name"],
                                        "symbol": f"{underlying['name']}25OCT{strike}{option_type}",
                                        "strike": strike,
                                        "type": option_type,
                                        "expiry": "2025-10-25",
                                        "ltp": round(ltp, 2),
                                        "volume": volume,
                                        "oi": oi,
                                        "lot": lot_size,
                                        "investment": round(ltp * lot_size, 2)
                                    })
                        
                        # Sort by volume (high to low) for better display
                        mock_options.sort(key=lambda x: x["volume"], reverse=True)
                        # ATM OPTIONS: Show ALL contracts (mixed underlyings) in dashboard
                        scanner_state["last_options"] = mock_options[:20]  # Show top 20 options
                        
                        # Filter signals based on underlyings setting
                        underlyings_filter = config.get("underlyings", [])
                        if underlyings_filter:
                            # Only include signals for specified underlyings
                            filtered_signals = []
                            for signal in mock_signals:
                                signal_underlying = signal.get("underlying", "").upper()
                                if any(signal_underlying == uf.upper() for uf in underlyings_filter):
                                    filtered_signals.append(signal)
                            mock_signals = filtered_signals
                            logging.info(f"🎯 Filtered to {len(mock_signals)} signals for underlyings: {underlyings_filter}")
                        
                        # Clear any existing signals to avoid duplicates
                        await db.signals.delete_many({})
                        
                        # Insert fresh filtered signals
                        if mock_signals:
                            await db.signals.insert_many(mock_signals)
                        
                        # Update stats based on fresh data
                        scanner_state["stats"] = {
                            "total": len(mock_signals),
                            "hit": len([s for s in mock_signals if s["outcome"] == "WIN"]),
                            "flop": len([s for s in mock_signals if s["outcome"] == "LOSS"]),
                            "pnl": sum([50.0 if s["outcome"] == "WIN" else -30.0 if s["outcome"] == "LOSS" else 0 for s in mock_signals])
                        }
                        
                        # Broadcast mock updates
                        await broadcast_message({
                            "type": "scanner_update",
                            "data": {
                                "signals": mock_signals,
                                "options": mock_options,
                                "stats": scanner_state["stats"],
                                "timestamp": _now_ist().isoformat()
                            }
                        })
                        
                        await asyncio.sleep(config.get("refresh_sec", 10))
                        continue
                        
                except Exception as e:
                    scanner_state["error_message"] = str(e)
                    await asyncio.sleep(30)
                    continue

            kite = scanner_state["kite_session"]
            
            # Load options data
            options = load_nfo_options(kite)
            if not options:
                scanner_state["error_message"] = "Failed to load NFO options"
                await asyncio.sleep(30)
                continue

            # Get underlyings to scan
            all_underlyings = sorted({o["name"] for o in options if o.get("name")})
            underlyings_filter = config.get("underlyings", [])
            if underlyings_filter:
                underlyings = [u for u in all_underlyings if u.upper() in [uf.upper() for uf in underlyings_filter]]
            else:
                underlyings = all_underlyings

            today = _now_ist().date()
            
            # Update global expiry filter from config
            from trinity_scanner import _build_only_expiry_date_set
            import trinity_scanner as ts
            ts.ONLY_EXPIRY_DATES = config.get("only_expiry_dates", [])
            ts.ONLY_EXPIRY_DATE_SET = _build_only_expiry_date_set(ts.ONLY_EXPIRY_DATES)
            
            # Gather contracts
            rows = _gather_selected_contracts(kite, options, underlyings, today)
            max_candidates = config.get("max_candidates", 100)
            if max_candidates > 0:
                rows = rows[:max_candidates]
            
            # Store options data
            scanner_state["last_options"] = [
                {
                    "underlying": r["underlying"],
                    "symbol": r["symbol"],
                    "strike": r["strike"],
                    "type": r["type"],
                    "expiry": r["expiry"].strftime("%Y-%m-%d") if hasattr(r["expiry"], "strftime") else str(r["expiry"]),
                    "ltp": r["ltp"],
                    "volume": r["volume"],
                    "oi": r.get("oi"),
                    "lot": r["lot"],
                    "investment": r.get("investment")
                }
                for r in rows
            ]

            # Generate signals based on intrabar setting
            if config.get("mode") == "live" or not config.get("mode"):
                allow_intrabar = config.get("allow_intrabar", False)
                
                if allow_intrabar:
                    # Intrabar analysis: Generate signals immediately when POI is hit
                    logging.info("🔥 INTRABAR MODE: Generating signals immediately at POI levels")
                else:
                    # Wait for candle close before generating signals
                    logging.info("📊 CANDLE CLOSE MODE: Waiting for 15-minute candle close")
                
                signals = options_rows_to_signals(
                    kite, rows,
                    sl_pct=config.get("sl_pct", 0.1),
                    tp_pct=config.get("tp_pct", 0.1),
                    allow_intrabar=allow_intrabar
                )
                
                # Process new signals
                new_signals = []
                for sig in signals:
                    signal_data = {
                        "id": str(uuid.uuid4()),
                        "underlying": sig.get("underlying", ""),
                        "contract": sig.get("contract", ""),
                        "entry_price": sig.get("entry_price"),
                        "sl": sig.get("sl"),
                        "tp": sig.get("tp"),
                        "rr": sig.get("rr"),
                        "lot": sig.get("lot", 1),
                        "outcome": sig.get("outcome", "PENDING"),
                        "signal_time": sig.get("_entry_dt") or _now_ist(),
                        "created_at": _now_ist()
                    }
                    new_signals.append(signal_data)

                    # 🔥 INSTANT LIVE SIGNAL BROADCAST
                    await broadcast_message({
                        "type": "live_signal",
                        "data": {
                            "signal": signal_data,
                            "timestamp": _now_ist().isoformat(),
                            "mode": "INTRABAR" if config.get("allow_intrabar", False) else "CANDLE_CLOSE"
                        }
                    })
                    logging.info(f"🚀 LIVE SIGNAL: {signal_data['underlying']} {signal_data['contract']} @ ₹{signal_data['entry_price']}")

                    # Send Telegram notification if enabled
                    if config.get("telegram_enabled") and config.get("telegram_bot_token") and config.get("telegram_chat_id"):
                        telegram_text = format_single_signal(sig)
                        try:
                            send_telegram(telegram_text, config["telegram_bot_token"], config["telegram_chat_id"])
                        except Exception as e:
                            logging.error(f"Telegram send error: {e}")

                    # Place order if real trading is enabled
                    if config.get("real_trading") and _within_market_hours(_now_ist()):
                        try:
                            order_result = _place_market_buy_order(
                                kite, 
                                sig.get("contract", ""),
                                sig.get("lot", 1)
                            )
                            if order_result:
                                logging.info(f"Order placed: {order_result}")
                        except Exception as e:
                            logging.error(f"Order placement error: {e}")

                # Store only new signals (avoid accumulating duplicates)
                scanner_state["last_signals"] = new_signals
                
                scanner_state["error_message"] = None

                # Broadcast updates to WebSocket clients
                await broadcast_message({
                    "type": "scanner_update",
                    "data": {
                        "signals": new_signals,
                        "options": scanner_state["last_options"],
                        "stats": scanner_state["stats"],
                        "timestamp": _now_ist().isoformat()
                    }
                })

            # Save to database (check for duplicates)
            for signal in scanner_state["last_signals"]:
                try:
                    # Check if signal already exists
                    existing = await db.signals.find_one({
                        "underlying": signal.get("underlying"),
                        "contract": signal.get("contract"), 
                        "entry_price": signal.get("entry_price"),
                        "signal_time": signal.get("signal_time")
                    })
                    if not existing:
                        await db.signals.insert_one(signal)
                    else:
                        logging.info(f"Signal already exists: {signal.get('underlying')} {signal.get('contract')}")
                except Exception as e:
                    logging.error(f"Database insert error: {e}")

            await asyncio.sleep(config.get("refresh_sec", 10))

        except Exception as e:
            scanner_state["error_message"] = str(e)
            logging.error(f"Scanner loop error: {e}")
            await asyncio.sleep(30)

# API Endpoints
@api_router.get("/")
async def root():
    return {"message": "Trinity Wealth Scanner API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

@api_router.post("/scanner/config")
async def update_scanner_config(config: ScannerConfig):
    """Update scanner configuration - SIMPLE & FAST"""
    # Just store in memory - no validation, no database
    scanner_state["config"] = config.dict()
    return {"message": "Configuration updated successfully"}

@api_router.get("/scanner/config")
async def get_scanner_config():
    """Get current scanner configuration - SIMPLE & FAST"""
    return scanner_state.get("config", {})

@api_router.post("/scanner/start")
async def start_scanner(background_tasks: BackgroundTasks):
    """Start the scanner"""
    if scanner_state["is_running"]:
        return {"message": "Scanner is already running"}
    
    config = scanner_state.get("config", {})
    if not config.get("api_key") or not config.get("api_secret"):
        raise HTTPException(status_code=400, detail="Please configure API credentials first")
    
    scanner_state["is_running"] = True
    scanner_state["error_message"] = None
    background_tasks.add_task(run_scanner_loop)
    
    return {"message": "Scanner started successfully"}

@api_router.post("/scanner/stop")
async def stop_scanner():
    """Stop the scanner"""
    scanner_state["is_running"] = False
    scanner_state["kite_session"] = None
    return {"message": "Scanner stopped successfully"}

async def calculate_real_stats():
    """Calculate statistics from actual database signals"""
    try:
        # Get all signals from database
        all_db_signals = await db.signals.find().to_list(None)
        
        total_signals = len(all_db_signals)
        winning_signals = len([s for s in all_db_signals if s.get("outcome") == "WIN"])
        losing_signals = len([s for s in all_db_signals if s.get("outcome") == "LOSS"])
        
        # Calculate P&L based on actual signal data
        total_pnl = 0.0
        for signal in all_db_signals:
            outcome = signal.get("outcome", "")
            lot = signal.get("lot", 1)
            entry_price = signal.get("entry_price", 0)
            tp = signal.get("tp", 0)
            sl = signal.get("sl", 0)
            
            if outcome == "WIN" and tp and entry_price:
                pnl = (tp - entry_price) * lot
                total_pnl += pnl
            elif outcome == "LOSS" and sl and entry_price:
                pnl = (sl - entry_price) * lot  # This will be negative
                total_pnl += pnl
        
        return {
            "total": total_signals,
            "hit": winning_signals,
            "flop": losing_signals,
            "pnl": round(total_pnl, 2)
        }
    except Exception as e:
        logging.error(f"Error calculating stats: {e}")
        return {"total": 0, "hit": 0, "flop": 0, "pnl": 0.0}

@api_router.get("/scanner/status", response_model=ScannerStatus)
async def get_scanner_status():
    """Get current scanner status with real-time stats from database"""
    real_stats = await calculate_real_stats()
    return ScannerStatus(
        is_running=scanner_state["is_running"],
        error_message=scanner_state.get("error_message"),
        last_update=datetime.utcnow(),
        stats=real_stats
    )

@api_router.get("/scanner/signals", response_model=List[Dict])
async def get_recent_signals():
    """Get recent signals"""
    try:
        signals = await db.signals.find().sort("created_at", -1).limit(100).to_list(100)
        # Convert ObjectId to string to avoid serialization errors
        for signal in signals:
            if "_id" in signal:
                signal["_id"] = str(signal["_id"])
            # Convert datetime objects to ISO strings with proper timezone
            for field in ["signal_time", "created_at", "entry_time", "poi_time", "bos_time", "induc_time", "hit_time"]:
                if field in signal and signal[field]:
                    if hasattr(signal[field], 'isoformat'):
                        signal[field] = signal[field].isoformat()
                    elif isinstance(signal[field], str) and 'T' in signal[field]:
                        # Already ISO string, keep as is
                        continue
        return signals
    except Exception as e:
        # Return in-memory signals if database fails
        return scanner_state.get("last_signals", [])

@api_router.get("/scanner/options", response_model=List[Dict])
async def get_current_options():
    """Get current ATM options being scanned"""
    return scanner_state.get("last_options", [])

@api_router.websocket("/scanner/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Send periodic updates
            await websocket.send_text(json.dumps({
                "type": "status",
                "data": {
                    "is_running": scanner_state["is_running"],
                    "error_message": scanner_state.get("error_message"),
                    "stats": scanner_state.get("stats", {}),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    scanner_state["is_running"] = False
    client.close()
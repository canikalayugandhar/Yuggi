#!/usr/bin/env python3
import time
import json
import ast
import re
import sys
import signal
import atexit
import traceback
import datetime as dt
from typing import List, Optional
import concurrent.futures
import pandas as pd
import requests  # used to send telegram messages

# Kite imports (optional)
try:
    from kiteconnect import KiteConnect, exceptions as kite_exceptions
except Exception:
    KiteConnect = None
    kite_exceptions = None

CONFIG_FILE = "kite_config.json"
import pytz
IST = pytz.timezone('Asia/Kolkata')

# ===== Settings =====
REFRESH_SEC = 10
INDEX_SET = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"}
MARKET_OPEN = dt.time(9, 0)
MARKET_CLOSE = dt.time(15, 30)
MIN_VOLUME = 1000
MIN_STRIKE = 1000
ATM_RANGE = 1  # +/- strikes around ATM
MAX_CANDIDATES = 100  # (0 means show all)
SHOW_ATM_TABLE = True  # default - can be overridden by config
ONLY_EXPIRY_DATES: List[str] = []


def _build_only_expiry_date_set(dates: List[str]) -> set:
    out = set()
    for s in dates or []:
        try:
            out.add(dt.date.fromisoformat(str(s)))
        except Exception:
            pass
    return out


ONLY_EXPIRY_DATE_SET = _build_only_expiry_date_set(ONLY_EXPIRY_DATES)


def _to_date(x) -> Optional[dt.date]:
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    return None


# ===== Trinity params =====
TF = "15minute"
HISTORICAL_DAYS = 5
MIN_CANDLES = 12
SWING_WINDOW = 4
INDUCEMENT_MAX_BARS = 30
WICK_PCT = 0.45
POI_LOOKBACK = 8
BUY_LIQ_LOOKAHEAD = 60
ENTRY_LOOKAHEAD = 240

# Parallelism
MAX_QUOTE_WORKERS = 12
MAX_HIST_WORKERS = 6
HIST_SLEEP_PER_WORKER = 0.03

# Intrabar
ALLOW_INTRABAR = False


# ===== Config loader (robust) =====
def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        pass
    try:
        cfg = ast.literal_eval(raw)
        if isinstance(cfg, dict):
            return cfg
    except Exception:
        pass
    cleaned = re.sub(r"//.*?$", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"#.*?$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r",\s*(?=[}\]])", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        try:
            cfg = ast.literal_eval(cleaned)
            if isinstance(cfg, dict):
                return cfg
        except Exception:
            pass
    return {}


def send_telegram(text: str, bot_token: str = None, chat_id: str = None) -> bool:
    """
    Send a plain-text message to Telegram.
    Returns True on HTTP 200, False otherwise or if config missing.
    """
    if not bot_token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        resp = requests.post(url, data=payload, timeout=6)
        return resp.status_code == 200
    except Exception:
        return False


def _strip_brackets(s: str) -> str:
    try:
        return re.sub(r"\s*\(.*?\)", "", str(s)).strip()
    except Exception:
        return str(s) if s is not None else ""


def format_single_signal(sig: dict) -> str:
    underlying_raw = sig.get("underlying") or ""
    contract_raw = sig.get("contract") or sig.get("symbol") or ""
    underlying = _strip_brackets(underlying_raw)
    contract = _strip_brackets(contract_raw)

    entry_price = sig.get("entry_price")
    sl = sig.get("sl")
    tp = sig.get("tp")
    rr = sig.get("rr")
    lot = sig.get("lot") or 1
    dtobj = sig.get("_entry_dt") or sig.get("entry_time") or sig.get("poi_time")
    outcome = (sig.get("outcome") or "").upper()

    timestr = "--:--:--"
    try:
        if dtobj and hasattr(dtobj, "astimezone"):
            timestr = dtobj.astimezone(IST).strftime("%H:%M:%S")
        elif dtobj:
            timestr = str(dtobj)
    except Exception:
        timestr = "--:--:--"

    parts = []
    if underlying:
        parts.append(underlying)
    if contract:
        parts.append(contract)
    parts.extend(
        [
            f"Signal Time: {timestr}",
            f"Entry: {entry_price if entry_price is not None else '--'}",
            f"SL: {sl if sl is not None else '--'}",
            f"TP: {tp if tp is not None else '--'}",
            f"RR: {rr if rr is not None else '--'}",
            f"Lot: {lot}",
        ]
    )

    if outcome == "WIN":
        parts.append("Hit")
    elif outcome == "LOSS":
        parts.append("Flop")
    elif outcome == "BOTH":
        parts.append("Hit+Flop")
    else:
        parts.append("Pending")

    return " | ".join(parts)


def _now_ist() -> dt.datetime:
    return dt.datetime.now(IST)


# ===== Kite session =====
def ensure_kite_session(api_key: str, api_secret: str, access_token: str = None):
    if KiteConnect is None:
        raise Exception("kiteconnect not installed. Install via `pip install kiteconnect`.")
    
    kite = KiteConnect(api_key=api_key)
    
    try:
        if access_token:
            kite.set_access_token(access_token)
        try:
            kite.quote(["NSE:RELIANCE"])
            return kite, access_token
        except Exception:
            # Access token expired/invalid, need to generate new one
            login_url = kite.login_url()
            raise Exception(f"Access token expired. Please login at: {login_url}")
    except Exception as e:
        raise Exception(f"Kite session error: {str(e)}")


# ===== Instruments & quotes =====
def load_nfo_options(kite):
    try:
        inst = kite.instruments("NFO")
        return [
            i
            for i in inst
            if i.get("instrument_type") in ("CE", "PE") and i.get("expiry") and i.get("name")
        ]
    except Exception:
        return []


def expiries_for_underlying(options, underlying, today):
    exps = sorted({o["expiry"] for o in options if o.get("name") == underlying})
    if not exps:
        return []
    if ONLY_EXPIRY_DATE_SET:
        filtered = []
        for e in exps:
            d = _to_date(e)
            if d in ONLY_EXPIRY_DATE_SET:
                filtered.append(e)
        return sorted(filtered)
    nearest = None
    for e in exps:
        if e >= today:
            nearest = e
            break
    if nearest is None:
        nearest = exps[0]
    result = [nearest]
    for e in exps:
        if e != nearest and 0 <= (e - today).days <= 7:
            result.append(e)
            break
    return sorted(list(dict.fromkeys(result)))


def get_spot(kite, underlying):
    idx_map = {
        "NIFTY": "NSE:NIFTY 50",
        "BANKNIFTY": "NSE:NIFTY BANK",
        "FINNIFTY": "NSE:NIFTY FIN SERVICE",
        "MIDCPNIFTY": "NSE:NIFTY MID SELECT",
    }
    try:
        key = idx_map.get(underlying.upper(), f"NSE:{underlying}")
        q = kite.quote([key])[key]
        return q["last_price"]
    except Exception:
        return None


def pick_atm_band_for_expiry(options, underlying, expiry, spot, k: int):
    same = [o for o in options if o.get("name") == underlying and o.get("expiry") == expiry]
    if not same or spot is None:
        return []
    strikes = sorted({int(o.get("strike")) for o in same if o.get("strike") is not None})
    if not strikes:
        return []
    atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot))
    start = max(0, atm_idx - max(0, int(k)))
    end = min(len(strikes) - 1, atm_idx + max(0, int(k)))
    chosen_strikes = strikes[start : end + 1]
    by_key = {(int(o["strike"]), o["instrument_type"]): o for o in same}
    out = []
    for s in chosen_strikes:
        for t in ("CE", "PE"):
            opt = by_key.get((s, t))
            if opt:
                out.append(opt)
    return out


def _fetch_quote_safe(kite, key):
    try:
        q = kite.quote([key])
        return key, q.get(key)
    except Exception:
        return key, None


def collect_option_rows(kite, opt_list, underlying, spot, expiries):
    out = []
    candidates = []
    for expiry in expiries:
        band_opts = pick_atm_band_for_expiry(opt_list, underlying, expiry, spot, ATM_RANGE)
        for opt in band_opts:
            if not opt:
                continue
            if int(opt.get("strike", 0)) <= MIN_STRIKE:
                continue
            candidates.append((expiry, opt))
    if not candidates:
        return out
    keys = [f"NFO:{opt['tradingsymbol']}" for _, opt in candidates]
    max_workers = min(MAX_QUOTE_WORKERS, max(2, len(keys)))
    quotes_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_quote_safe, kite, k): k for k in keys}
        for fut in concurrent.futures.as_completed(futures):
            key = futures[fut]
            try:
                k, res = fut.result()
                quotes_map[k] = res
            except Exception:
                quotes_map[key] = None
    seen_symbols = set()
    for (expiry, opt) in candidates:
        ts = opt["tradingsymbol"]
        if ts in seen_symbols:
            continue
        seen_symbols.add(ts)
        key = f"NFO:{ts}"
        q = quotes_map.get(key)
        if not q:
            continue
        ltp = q.get("last_price")
        ohlc = q.get("ohlc") or {}
        pc = ohlc.get("close")
        vol = q.get("volume") or q.get("volume_traded")
        oi = q.get("oi")
        lot = opt.get("lot_size")
        if not isinstance(ltp, (int, float)) or not isinstance(pc, (int, float)):
            continue
        if not (isinstance(vol, (int, float)) and vol >= MIN_VOLUME):
            continue
        investment = lot * ltp if isinstance(lot, int) and isinstance(ltp, (int, float)) else None
        out.append(
            {
                "underlying": underlying,
                "expiry": expiry,
                "strike": int(opt["strike"]),
                "type": opt["instrument_type"],
                "symbol": ts,
                "lot": lot,
                "ltp": ltp,
                "prev_close": pc,
                "volume": vol,
                "oi": oi,
                "investment": investment,
                "is_index": (underlying in INDEX_SET),
                "token": opt.get("instrument_token"),
            }
        )
    return out


def _gather_selected_contracts(kite, options, underlyings, today):
    all_rows = []
    for u in underlyings:
        spot = get_spot(kite, u)
        expiries = expiries_for_underlying(options, u, today)
        if not spot or not expiries:
            continue
        rows = collect_option_rows(kite, options, u, spot, expiries)
        all_rows += rows
    all_rows.sort(key=lambda r: (r.get("volume") is None, r.get("volume") or 0, r.get("ltp") or 0), reverse=True)
    return all_rows


# ===== Trading pattern utilities =====
def is_swing_high(candles, idx, window=SWING_WINDOW):
    try:
        h = candles[idx]["high"]
        left = max(c["high"] for c in candles[max(0, idx - window) : idx]) if idx - window >= 0 else -1e12
        right = max(c["high"] for c in candles[idx + 1 : idx + 1 + window]) if idx + 1 + window <= len(candles) else -1e12
        return (h > left) and (h >= right)
    except Exception:
        return False


def is_swing_low(candles, idx, window=SWING_WINDOW):
    try:
        l = candles[idx]["low"]
        left = min(c["low"] for c in candles[max(0, idx - window) : idx]) if idx - window >= 0 else 1e12
        right = min(c["low"] for c in candles[idx + 1 : idx + 1 + window]) if idx + 1 + window <= len(candles) else 1e12
        return (l < left) and (l <= right)
    except Exception:
        return False


def find_swings(candles, window=SWING_WINDOW):
    highs, lows = [], []
    n = len(candles)
    for i in range(window, n - window):
        if is_swing_high(candles, i, window):
            highs.append(i)
        if is_swing_low(candles, i, window):
            lows.append(i)
    return highs, lows


def detect_bullish_bos(candles):
    highs, _ = find_swings(candles)
    if not highs:
        return None
    prev_hi_idx = highs[-2] if len(highs) >= 2 else highs[-1]
    prev_hi_price = candles[prev_hi_idx]["high"]
    for i in range(prev_hi_idx + 1, len(candles)):
        if candles[i]["close"] > prev_hi_price:
            return {"type": "bull", "break_index": i, "break_price": candles[i]["close"], "prev_swing_index": prev_hi_idx}
    return None


def detect_inducement_after_bos(candles, bos_info, max_bars=INDUCEMENT_MAX_BARS, wick_pct=WICK_PCT):
    start = bos_info["break_index"] + 1
    end = min(len(candles), start + max_bars)
    for i in range(start, end):
        o, c, h, l = candles[i]["open"], candles[i]["close"], candles[i]["high"], candles[i]["low"]
        rng = h - l
        if rng <= 0:
            continue
        upper_wick = h - max(o, c)
        if c < o and (upper_wick / rng) >= wick_pct:
            return {"index": i, "open": o, "close": c, "high": h, "low": l}
    return None


def find_buy_side_liquidity_smc(candles, after_index, lookahead=BUY_LIQ_LOOKAHEAD):
    start = after_index + 1
    seg = candles[start : start + lookahead] if start < len(candles) else candles[-lookahead:]
    highs = [c["high"] for c in seg if c.get("high") is not None]
    return max(highs) if highs else None


def find_poi_from_inducement(candles, inducement, lookback=POI_LOOKBACK):
    idx = inducement["index"]
    start = max(0, idx - lookback)
    lows = [(i, candles[i]["low"]) for i in range(start, idx + 1)]
    sel_idx, sel_low = min(lows, key=lambda x: x[1])
    return {"index": sel_idx, "price": sel_low, "low": sel_low}


def simulate_outcome(candles, entry_idx, entry_price, tp_price, sl_price, lookahead=ENTRY_LOOKAHEAD):
    n = len(candles)
    start = entry_idx + 1
    end = min(n, start + lookahead)
    for i in range(start, end):
        hi = candles[i]["high"]
        lo = candles[i]["low"]
        ts = candles[i].get("date")
        hit_tp = hi >= tp_price
        hit_sl = lo <= sl_price
        if hit_tp and not hit_sl:
            return {"result": "WIN", "hit_index": i, "hit_time": ts, "hit_price": tp_price}
        if hit_sl and not hit_tp:
            return {"result": "LOSS", "hit_index": i, "hit_time": ts, "hit_price": sl_price}
        if hit_tp and hit_sl:
            return {"result": "BOTH", "hit_index": i, "hit_time": ts, "hit_price": tp_price}
    return {"result": "NO_HIT", "hit_index": None, "hit_time": None, "hit_price": None}


def run_ymc_scan_on_candles(candles, min_candles_required: Optional[int] = None, sl_pct: float = 0.1, tp_pct: float = 0.1):
    signals = []
    search = 0
    threshold = MIN_CANDLES if min_candles_required is None else int(min_candles_required)
    while True:
        sub = candles[search:]
        if len(sub) < SWING_WINDOW * 3 or len(sub) < threshold:
            break
        bos = detect_bullish_bos(sub)
        if not bos:
            break
        bos_idx = search + bos["break_index"]
        induc = detect_inducement_after_bos(candles, {"break_index": bos_idx})
        if not induc:
            search = bos_idx + 1
            continue
        induc_idx = induc["index"]
        poi = find_poi_from_inducement(candles, induc)
        buy_liq = find_buy_side_liquidity_smc(candles, induc_idx)
        if not poi or not buy_liq:
            search = induc_idx + 1
            continue

        # ===== NEW CONDITION: POI must be greater than previous day's low =====
        try:
            poi_dt = candles[poi["index"]].get("date")
            if poi_dt is not None:
                poi_day = pd.to_datetime(poi_dt).date()
                prev_day = poi_day - dt.timedelta(days=1)
                prev_day_candles = [c for c in candles if pd.to_datetime(c["date"]).date() == prev_day]
                if prev_day_candles:
                    prev_day_low = min(c["low"] for c in prev_day_candles)
                    if poi["price"] <= prev_day_low:
                        search = induc_idx + 1
                        continue
        except Exception:
            pass

        # ===== Configurable percentage-based SL/TP =====
        SL_PCT = sl_pct / 100.0  # convert percentage to decimal
        TP_PCT = tp_pct / 100.0

        entry_price = round(poi["price"], 2)
        sl_price = round(entry_price * (1 - SL_PCT), 2)
        tp_price = round(buy_liq * (1 - TP_PCT), 2) if buy_liq is not None else None

        poi_time = candles[poi["index"]].get("date") if poi and poi.get("index") is not None else None
        entry_idx = poi["index"]
        entry_time = poi_time
        rr = (tp_price - entry_price) / (entry_price - sl_price) if (entry_price > sl_price and tp_price is not None) else 0.0
        outcome = simulate_outcome(candles, entry_idx, entry_price, tp_price, sl_price)
        signals.append(
            {
                "bos_index": bos_idx,
                "induc_index": induc_idx,
                "entry_index": entry_idx,
                "entry_price": entry_price,
                "sl": sl_price,
                "tp": tp_price,
                "rr": round(rr, 2),
                "outcome": outcome["result"],
                "bos_time": candles[bos_idx].get("date"),
                "induc_time": candles[induc_idx].get("date"),
                "entry_time": entry_time,
                "poi_time": poi_time,
                "hit_time": outcome.get("hit_time"),
                "exit_price": outcome.get("hit_price"),
            }
        )
        search = entry_idx + 1
    return signals


# ===== Historical fetch and parsing =====
def _append_intrabar_candle(candles, live_price, live_ts=None):
    if not candles or live_price is None:
        return candles
    try:
        last = candles[-1]
        last_close = float(last.get("close") or 0.0)
    except Exception:
        return candles
    o = last_close
    c = float(live_price)
    h = max(o, c, float(last.get("high") or o))
    l = min(o, c, float(last.get("low") or o))
    vol = float(last.get("volume") or 0.0)
    new_candle = {"date": live_ts or last.get("date"), "open": o, "high": h, "low": l, "close": c, "volume": vol}
    return candles[:-1] + [new_candle]


def _fetch_historical_safe(kite, token, from_dt, to_dt, tf):
    try:
        try:
            raw = kite.historical_data(int(token), from_dt, to_dt, tf, continuous=False)
        except TypeError:
            raw = kite.historical_data(int(token), from_dt, to_dt, tf)
        return token, raw
    except Exception:
        return token, None


def _parse_to_dtobj(ts):
    if not ts:
        return None
    try:
        if hasattr(ts, "to_pydatetime"):
            dtobj = ts.to_pydatetime()
        else:
            dtobj = pd.to_datetime(str(ts))
        if hasattr(dtobj, "tz_localize"):
            if dtobj.tzinfo is None:
                dtobj = dtobj.tz_localize(IST)
        if isinstance(dtobj, pd.Timestamp):
            dtobj = dtobj.to_pydatetime()
        if isinstance(dtobj, dt.datetime) and dtobj.tzinfo is None:
            dtobj = dtobj.replace(tzinfo=IST)
        return dtobj
    except Exception:
        try:
            return dt.datetime.fromisoformat(str(ts))
        except Exception:
            return None


def options_rows_to_signals(kite, rows, sl_pct: float = 0.1, tp_pct: float = 0.1, allow_intrabar: bool = False):
    signals = []
    if not rows:
        return signals
    today_date = _now_ist().date()
    hist_days = HISTORICAL_DAYS
    token_rows = [(r.get("token"), r) for r in rows if r.get("token")]
    if not token_rows:
        return []
    to_dt = _now_ist()
    from_dt = to_dt - dt.timedelta(days=hist_days)
    max_workers = min(MAX_HIST_WORKERS, max(2, len(token_rows)))
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures_map = {}
        for token, r in token_rows:
            fut = ex.submit(_fetch_historical_safe, kite, token, from_dt, to_dt, TF)
            futures_map[fut] = r
            time.sleep(HIST_SLEEP_PER_WORKER)
        for fut in concurrent.futures.as_completed(futures_map):
            row = futures_map[fut]
            try:
                token, raw = fut.result()
            except Exception:
                token, raw = None, None
            if not raw:
                continue
            candles = []
            for c in raw:
                try:
                    candles.append(
                        {
                            "date": c.get("date"),
                            "open": float(c.get("open") or c.get("o") or 0.0),
                            "high": float(c.get("high") or c.get("h") or 0.0),
                            "low": float(c.get("low") or c.get("l") or 0.0),
                            "close": float(c.get("close") or c.get("c") or 0.0),
                            "volume": float(c.get("volume") or c.get("v") or 0.0),
                        }
                    )
                except Exception:
                    continue
            if len(candles) < MIN_CANDLES:
                continue
            if allow_intrabar:
                try:
                    qkey = f"NFO:{row.get('symbol')}"
                    q = None
                    try:
                        q = kite.quote([qkey]).get(qkey)
                    except Exception:
                        q = None
                    if q and isinstance(q.get("last_price"), (int, float)):
                        live_ltp = q.get("last_price")
                        live_ts = q.get("timestamp") if q.get("timestamp") else _now_ist()
                        candles = _append_intrabar_candle(candles, live_ltp, live_ts)
                except Exception:
                    pass
            smc_signals = run_ymc_scan_on_candles(candles, min_candles_required=MIN_CANDLES, sl_pct=sl_pct, tp_pct=tp_pct)
            filtered = []
            for s in smc_signals:
                try:
                    entry_dt = _parse_to_dtobj(s.get("entry_time"))
                    if not entry_dt or entry_dt.date() != today_date:
                        continue
                    if entry_dt.hour < 9 or (entry_dt.hour == 9 and entry_dt.minute < 30):
                        continue
                    entry = float(s.get("entry_price"))
                    sl = float(s.get("sl"))
                    tp = float(s.get("tp")) if s.get("tp") is not None else None
                    risk = entry - sl
                    reward = tp - entry if tp is not None else None
                    if risk > 0 and reward is not None and reward > 0:
                        s["contract"] = row.get("symbol") or row.get("symbol")
                        s["underlying"] = row.get("underlying") if "underlying" in row else row.get("underlying", "")
                        s["ltp"] = row.get("ltp")
                        s["lot"] = row.get("lot") or 1
                        s["_entry_dt"] = entry_dt
                        s["_risk"] = round(risk, 2)
                        s["_reward"] = round(reward, 2)
                        filtered.append(s)
                except Exception:
                    continue
            results.extend(filtered)
    results.sort(key=lambda x: x.get("_entry_dt"))
    return results


def _within_market_hours(now_dt: dt.datetime) -> bool:
    local = now_dt.astimezone(IST)
    t = local.time().replace(tzinfo=None)
    return MARKET_OPEN <= t <= MARKET_CLOSE


def _place_market_buy_order(kite, tradingsymbol: str, quantity: int) -> Optional[dict]:
    if not tradingsymbol or not isinstance(quantity, int) or quantity <= 0:
        return None
    qkey = f"NFO:{tradingsymbol}"
    limit_price = None
    try:
        q = kite.quote([qkey]).get(qkey)
        if q and isinstance(q.get("last_price"), (int, float)):
            limit_price = round(float(q.get("last_price")), 2)
    except Exception:
        limit_price = None
    if limit_price is None:
        try:
            ltp_resp = kite.ltp([qkey])
            if ltp_resp and ltp_resp.get(qkey) and isinstance(ltp_resp[qkey].get("last_price"), (int, float)):
                limit_price = round(float(ltp_resp[qkey]["last_price"]), 2)
        except Exception:
            limit_price = None
    if limit_price is None:
        return None
    try:
        order_id = kite.place_order(
            variety="regular",
            exchange="NFO",
            tradingsymbol=tradingsymbol,
            transaction_type="BUY",
            quantity=quantity,
            order_type="LIMIT",
            price=limit_price,
            product="MIS",
            validity="DAY",
        )
        return {"order_id": order_id, "price": limit_price}
    except Exception as e:
        raise Exception(f"Order failed for {tradingsymbol} qty {quantity} price {limit_price}: {str(e)}")
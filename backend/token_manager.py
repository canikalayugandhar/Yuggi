"""
Access Token Manager - Save token for the trading day
"""
import os
import json
import datetime as dt
from pathlib import Path

TOKEN_FILE = "/app/backend/daily_access_token.json"

def save_access_token(api_key: str, access_token: str):
    """Save access token with today's date"""
    today = dt.date.today().isoformat()
    token_data = {
        "date": today,
        "api_key": api_key[:8] + "...",  # Store partial key for verification
        "access_token": access_token,
        "created_at": dt.datetime.now().isoformat()
    }
    
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f)
    
    print(f"✅ Access token saved for {today}")

def get_daily_access_token(api_key: str) -> str:
    """Get today's access token if available"""
    if not os.path.exists(TOKEN_FILE):
        return None
    
    try:
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
        
        today = dt.date.today().isoformat()
        stored_date = token_data.get("date")
        stored_key_partial = token_data.get("api_key")
        current_key_partial = api_key[:8] + "..."
        
        # Check if token is for today and same API key
        if (stored_date == today and 
            stored_key_partial == current_key_partial):
            
            print(f"✅ Using saved access token for {today}")
            return token_data.get("access_token")
        else:
            print(f"❌ Token expired or different API key")
            return None
            
    except Exception as e:
        print(f"❌ Error reading token file: {e}")
        return None

def clear_old_tokens():
    """Clear tokens older than today"""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
            
            today = dt.date.today().isoformat()
            if token_data.get("date") != today:
                os.remove(TOKEN_FILE)
                print(f"✅ Cleared old token file")
        except:
            pass
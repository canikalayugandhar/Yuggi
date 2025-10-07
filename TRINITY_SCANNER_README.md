# Trinity Wealth Scanner - Desktop Application

A comprehensive full-stack web application for real-time options trading signal generation using advanced technical analysis patterns. Built with FastAPI backend and React frontend.

## 🚀 Features

### ✅ **Real-time Options Scanning**
- Scans NFO (National Stock Exchange Futures & Options) contracts
- Monitors NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY indices
- ATM (At-The-Money) options analysis
- Volume and open interest filtering

### ✅ **Advanced Technical Analysis**
- **Trinity Trading Patterns**: Sophisticated pattern recognition
- **Break of Structure (BOS)**: Identifies key market structure breaks
- **Inducement Detection**: Spots market inducement patterns  
- **Point of Interest (POI)**: Locates optimal entry points
- **Smart Money Concepts**: Implements institutional trading logic

### ✅ **Signal Generation**
- Automated entry, stop-loss, and take-profit calculation
- Risk-reward ratio analysis
- Real-time signal outcome tracking (Win/Loss/Pending)
- Historical performance statistics

### ✅ **Trading Modes**
- **Live Trading**: Real-time market data and signal generation
- **Backtest Mode**: Historical data analysis and strategy testing
- **Paper Trading**: Risk-free signal testing

### ✅ **Notifications & Automation**
- Optional Telegram notifications for new signals
- Real-time dashboard updates
- Automated order placement (when enabled)
- Market hours validation

### ✅ **Professional Dashboard**
- Real-time signals table with complete trade details
- ATM options monitoring with volume/OI data
- Performance statistics and P&L tracking
- Comprehensive configuration management

## 🛠️ Setup & Installation

### Prerequisites
- **Kite Connect API**: Valid API credentials from Zerodha
- **Python 3.11+**: Backend runtime
- **Node.js 18+**: Frontend development
- **MongoDB**: Database for storing signals and configurations

### Quick Start

1. **Configure API Credentials**
   - Navigate to the "Settings" tab in the application
   - Enter your Kite Connect API Key and Secret
   - Access token will be auto-generated on first login

2. **Configure Trading Parameters**
   ```
   Stop Loss %: 0.1% (default)
   Take Profit %: 0.1% (default)  
   Min Volume: 1000 (contracts)
   Max Candidates: 100 (top options to scan)
   ATM Range: 1 (strikes around ATM)
   ```

3. **Optional: Setup Telegram Notifications**
   - Create a Telegram bot via @BotFather
   - Get your chat ID
   - Enable notifications in Settings

4. **Start Scanning**
   - Click "Start Scanner" to begin real-time monitoring
   - Monitor signals in Dashboard and Signals tabs
   - View ATM options data in Options tab

## 📊 Dashboard Overview

### **Statistics Cards**
- **Total Signals**: Count of all generated signals
- **Winning Signals**: Successful trades count
- **Losing Signals**: Failed trades count  
- **Total P&L**: Cumulative profit/loss

### **Recent Signals Panel**
- Latest 5 trading signals
- Entry prices and outcomes
- Real-time signal status updates

### **Top ATM Options Panel**  
- High volume options being monitored
- LTP (Last Traded Price) information
- Volume and lot size data

## 🔧 Configuration Options

### **API Configuration**
```json
{
  "api_key": "your_kite_api_key",
  "api_secret": "your_kite_api_secret", 
  "access_token": "auto_generated"
}
```

### **Trading Settings**
```json
{
  "mode": "live",           // "live" or "backtest"
  "real_trading": false,    // Enable actual order placement
  "sl_pct": 0.1,           // Stop loss percentage  
  "tp_pct": 0.1,           // Take profit percentage
  "min_volume": 1000,      // Minimum volume filter
  "max_candidates": 100    // Maximum contracts to scan
}
```

### **Advanced Settings**
```json
{
  "underlyings": ["NIFTY", "BANKNIFTY"],        // Specific indices (empty = all)
  "atm_range": 1,                               // Strikes around ATM
  "refresh_sec": 10,                            // Scan interval seconds
  "allow_intrabar": false,                      // Enable intrabar analysis
  "only_expiry_dates": ["2025-10-17", "2025-10-24"]  // Specific expiry dates
}
```

### **Expiry Date Selection**
The Trading Settings now includes a sophisticated expiry date selector:

- **Auto-Selection (Default)**: Leave empty for automatic selection of nearest and weekly expiries
- **Manual Selection**: Use the date picker to add specific expiry dates
- **Quick Select**: Choose from suggested typical expiry Thursdays
- **Monthly Expiries**: Automatically highlighted in the suggestions
- **Multiple Dates**: Select as many expiry dates as needed
- **Visual Management**: Easy-to-remove badge interface for selected dates

### **Telegram Integration**
```json
{
  "telegram_enabled": true,
  "telegram_bot_token": "your_bot_token", 
  "telegram_chat_id": "your_chat_id"
}
```

## 📈 Signal Information

Each generated signal contains:

- **Time**: Signal generation timestamp
- **Underlying**: Index (NIFTY, BANKNIFTY, etc.)
- **Contract**: Specific option contract symbol
- **Entry**: Optimal entry price
- **SL**: Stop loss level
- **TP**: Take profit target
- **R:R**: Risk-reward ratio
- **Lot**: Recommended lot size
- **Outcome**: Win/Loss/Pending status

## 🎯 Trading Strategy

The Trinity Wealth Scanner implements advanced Smart Money Concepts:

1. **Structure Break Detection**: Identifies when price breaks previous swing highs/lows
2. **Inducement Analysis**: Spots false moves designed to trap retail traders  
3. **POI Identification**: Locates institutional order blocks and fair value gaps
4. **Liquidity Mapping**: Identifies areas where institutional orders may be placed

## ⚠️ Risk Disclaimer

**IMPORTANT**: This is a trading tool for educational and analysis purposes. 

- **Paper Trade First**: Test strategies without real money
- **Risk Management**: Never risk more than you can afford to lose
- **Market Volatility**: Options trading involves significant risk
- **No Guarantees**: Past performance does not guarantee future results

## 🔐 Security & Privacy

- API credentials are stored securely in the database
- All communications use HTTPS encryption
- No sensitive data is logged or transmitted unnecessarily
- Optional Telegram notifications for privacy-conscious users

## 📞 Support

For technical support or questions about the Trinity Wealth Scanner:

1. Check the error messages in the dashboard
2. Verify your API credentials in Settings
3. Ensure market hours for live trading (9:00 AM - 3:30 PM IST)
4. Review the backend logs for detailed error information

## 🚀 Advanced Usage

### Real Trading Mode
- Enable "Real Trading" in Settings only after thorough testing
- Ensure sufficient margin in your trading account
- Monitor positions actively during market hours
- Use appropriate position sizing

### Backtest Mode  
- Analyze historical patterns and performance
- Test different parameter configurations
- Validate strategy effectiveness before live trading
- Review win/loss ratios and risk metrics

## 📋 System Requirements

- **Minimum RAM**: 4GB (8GB recommended)
- **Internet**: Stable broadband connection for real-time data
- **Browser**: Modern browser (Chrome, Firefox, Safari)
- **Market Data**: Active Kite Connect subscription

---

**Built with**: FastAPI, React, MongoDB, Kite Connect API, Tailwind CSS

**Version**: 1.0.0  
**Last Updated**: October 2025
# Trinity Wealth Scanner - Desktop Setup Guide

## 🖥️ Run Trinity Wealth Scanner on Your Desktop

### **Prerequisites**
1. **Python 3.8+** - [Download from python.org](https://www.python.org/downloads/)
2. **Node.js 16+** - [Download from nodejs.org](https://nodejs.org/downloads/)
3. **MongoDB Community** - [Download from mongodb.com](https://www.mongodb.com/try/download/community)

### **Quick Setup (5 Minutes)**

#### **Step 1: Download & Extract**
1. Download the `trinity_scanner_desktop.zip` package
2. Extract to your desired folder (e.g., `C:\TrinityScanner` or `~/TrinityScanner`)

#### **Step 2: Install Dependencies**
```bash
# Navigate to the folder
cd trinity_scanner_desktop

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies  
cd frontend
npm install
cd ..
```

#### **Step 3: Start MongoDB**
- **Windows**: Start MongoDB service from Services panel
- **Mac/Linux**: `brew services start mongodb-community` or `sudo systemctl start mongod`

#### **Step 4: Start the Application**
```bash
# Option A: Use the start script (easiest)
./start_desktop.bat    # Windows
./start_desktop.sh     # Mac/Linux

# Option B: Manual start
# Terminal 1 - Start Backend
cd backend
python server.py

# Terminal 2 - Start Frontend  
cd frontend
npm start
```

#### **Step 5: Access the Application**
- Open your browser and go to: `http://localhost:3000`
- The Trinity Wealth Scanner will be running locally on your desktop!

### **Desktop Configuration**

#### **Environment Setup**
The desktop version uses these local URLs:
- **Frontend**: `http://localhost:3000`
- **Backend**: `http://localhost:8001`
- **Database**: `mongodb://localhost:27017`

#### **Kite API Setup**
1. Go to Settings tab
2. Enter your Kite API credentials:
   - API Key: Your Zerodha API Key
   - API Secret: Your Zerodha API Secret
   - Access Token: Generate daily from Kite Connect
3. Save Configuration

### **Features Available on Desktop**
- ✅ Real-time signal generation
- ✅ Live options data (ATM contracts)
- ✅ Win/Loss outcome monitoring  
- ✅ P&L calculations
- ✅ Configuration persistence
- ✅ All dashboard functionality

### **Desktop vs Cloud Differences**
| Feature | Desktop | Cloud |
|---------|---------|--------|
| Performance | Faster (local) | Depends on internet |
| Data Privacy | Complete privacy | Shared infrastructure |
| Setup | One-time setup | No setup needed |
| Updates | Manual | Automatic |
| Access | Local only | Anywhere |

### **Troubleshooting**

#### **Common Issues**
1. **"MongoDB connection failed"**
   - Ensure MongoDB is running: `mongod --version`
   - Check if port 27017 is free

2. **"Backend not starting"**  
   - Check Python version: `python --version`
   - Install missing packages: `pip install -r requirements.txt`

3. **"Frontend not loading"**
   - Check Node.js version: `node --version`
   - Clear cache: `npm cache clean --force`

#### **Port Conflicts**
If ports 3000 or 8001 are busy:
```bash
# Change frontend port
PORT=3001 npm start

# Change backend port in server.py
app.run(host="0.0.0.0", port=8002)
```

### **Performance Tips**
- **RAM**: 4GB minimum, 8GB recommended
- **CPU**: Dual-core minimum for real-time scanning  
- **Storage**: 1GB free space for data and logs
- **Network**: Stable internet for Kite API calls

### **Data Backup**
Your signals and configurations are stored locally in MongoDB:
```bash
# Backup your data
mongodump --db trinity_scanner --out backup/

# Restore data
mongorestore --db trinity_scanner backup/trinity_scanner/
```

---

## 🚀 **Ready to Trade!**

Once setup is complete, you'll have a fully functional Trinity Wealth Scanner running privately on your desktop with all the same features as the cloud version!

**Need help?** Check the troubleshooting section or run the diagnostic script: `python check_setup.py`
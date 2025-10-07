#!/bin/bash

echo "========================================"
echo "  Trinity Wealth Scanner - Desktop"
echo "========================================"
echo "Starting Trinity Wealth Scanner locally..."
echo ""

# Check if MongoDB is running
echo "[1/4] Checking MongoDB..."
if pgrep -x "mongod" > /dev/null; then
    echo "✅ MongoDB is running"
elif brew services list | grep mongodb | grep started > /dev/null 2>&1; then
    echo "✅ MongoDB is running (via Homebrew)"
elif systemctl is-active --quiet mongod; then
    echo "✅ MongoDB is running (systemd)"
else
    echo "❌ MongoDB not detected. Starting MongoDB..."
    
    # Try to start MongoDB
    if command -v brew >/dev/null 2>&1; then
        echo "   Starting via Homebrew..."
        brew services start mongodb-community
    elif command -v systemctl >/dev/null 2>&1; then
        echo "   Starting via systemd..."
        sudo systemctl start mongod
    else
        echo "   Please start MongoDB manually:"
        echo "   - Install from: https://www.mongodb.com/try/download/community"
        echo "   - Run: mongod --dbpath /path/to/data/directory"
        read -p "Press enter when MongoDB is running..."
    fi
fi

# Start Backend
echo ""
echo "[2/4] Starting Backend Server..."
cd backend || { echo "❌ Backend directory not found"; exit 1; }

# Start backend in background
python server.py &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID) on http://localhost:8001"

# Wait for backend to start
sleep 3

# Start Frontend
echo ""
echo "[3/4] Starting Frontend..."
cd ../frontend || { echo "❌ Frontend directory not found"; exit 1; }

# Start frontend in background
npm start &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID) on http://localhost:3000"

# Wait for frontend to start
echo "   Waiting for frontend to initialize..."
sleep 8

# Open in browser
echo ""
echo "[4/4] Opening Trinity Wealth Scanner..."
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open http://localhost:3000
elif command -v open >/dev/null 2>&1; then
    open http://localhost:3000
else
    echo "   Please open: http://localhost:3000 in your browser"
fi

echo ""
echo "========================================"
echo "✅ Trinity Wealth Scanner is running!"
echo "========================================"
echo ""
echo "📊 Dashboard: http://localhost:3000"  
echo "🔧 Backend API: http://localhost:8001"
echo "💾 Database: mongodb://localhost:27017"
echo ""
echo "🔄 To stop the scanner:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "📱 The application is now running locally!"

# Create stop script
cat > stop_desktop.sh << EOF
#!/bin/bash
echo "Stopping Trinity Wealth Scanner..."
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
echo "✅ Scanner stopped"
EOF

chmod +x stop_desktop.sh
echo "💡 Run ./stop_desktop.sh to stop all services"
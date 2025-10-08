import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";
import { Play, Square, Settings, Activity, TrendingUp, AlertCircle, CheckCircle2 } from "lucide-react";
import ExpiryDateSelector from "@/components/ExpiryDateSelector";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [config, setConfig] = useState({
    api_key: "jdhb0gprnxjr1k31",
    api_secret: "4qnsimdyhlrgm3tqk7toiosu8u2i9wsg",
    access_token: "",
    real_trading: false,
    telegram_enabled: false,
    telegram_bot_token: "",
    telegram_chat_id: "",
    atm_range: 1,
    min_volume: 1000,
    min_strike: 2000,
    refresh_sec: 10,
    max_candidates: 100,
    show_atm_table: true,
    sl_pct: 0.1,
    tp_pct: 0.1,
    allow_intrabar: false,
    mode: "live",
    underlyings: [],
    only_expiry_dates: []
  });
  
  const [scannerStatus, setScannerStatus] = useState({
    is_running: false,
    error_message: null,
    last_update: null,
    stats: { total: 0, hit: 0, flop: 0, pnl: 0.0 }
  });
  
  // Simple stats calculation from signals
  const calculateStatsFromSignals = (signalsList) => {
    const total = signalsList.length;
    const wins = signalsList.filter(s => s.outcome === 'WIN').length;
    const losses = signalsList.filter(s => s.outcome === 'LOSS').length;
    
    // Simple P&L calculation: (exit_price - entry_price) * lot
    let totalPnL = 0;
    signalsList.forEach(signal => {
      if (signal.outcome === 'WIN' || signal.outcome === 'LOSS') {
        if (signal.exit_price && signal.entry_price && signal.lot) {
          const pnl = (signal.exit_price - signal.entry_price) * signal.lot;
          totalPnL += pnl;
        }
      }
    });
    
    return {
      total: total,
      hit: wins,
      flop: losses,
      pnl: totalPnL
    };
  };
  
  const [signals, setSignals] = useState([]);
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveStatus, setSaveStatus] = useState('idle'); // 'idle', 'saving', 'saved', 'error'
  const [currentTime, setCurrentTime] = useState(new Date());
  const [activeTab, setActiveTab] = useState("dashboard");
  const { toast } = useToast();

  // Load configuration on component mount and tab changes
  useEffect(() => {
    loadConfig();
    loadScannerStatus();
    loadRecentSignals();
    loadCurrentOptions();
    
    // 🎯 FORCE STATS UPDATE - Auto-refresh every 10 seconds
    const statsInterval = setInterval(() => {
      loadRecentSignals(); // This will recalculate stats
    }, 10000);
    
    return () => clearInterval(statsInterval);
  }, []);
  
  // Reload config when returning to settings tab
  useEffect(() => {
    if (activeTab === 'settings') {
      loadConfig();
      // Check if config was recently saved
      const savedTimestamp = localStorage.getItem('trinity_config_saved');
      const now = Date.now();
      if (savedTimestamp && (now - parseInt(savedTimestamp)) < 1800000) { // Within 30 minutes
        setSaveStatus('saved');
        // Keep saved status visible much longer
        setTimeout(() => setSaveStatus('idle'), 300000); // 5 minutes
      }
    }
  }, [activeTab]);

  // Real-time clock update
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000); // Update every second
    
    return () => clearInterval(timer);
  }, []);

  // WebSocket and polling setup
  useEffect(() => {
    // 🚀 WebSocket connection for LIVE signals
    const connectWebSocket = () => {
      const wsUrl = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://') + '/api/scanner/ws';
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('🔥 LIVE Signal WebSocket connected');
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'live_signal') {
            // 🚀 INSTANT LIVE SIGNAL UPDATE
            const newSignal = data.data.signal;
            setSignals(prev => [newSignal, ...prev]);
            
            // Show live signal notification
            toast({
              title: "🚀 LIVE SIGNAL!",
              description: `${newSignal.underlying} ${newSignal.contract} @ ₹${newSignal.entry_price}`,
              variant: "default",
              duration: 5000
            });
            
            console.log('🎯 LIVE SIGNAL:', newSignal);
          } else if (data.type === 'outcome_update') {
            // 🎯 REAL-TIME OUTCOME UPDATE
            const outcomeData = data.data;
            
            // Update signals in state
            setSignals(prev => prev.map(signal => {
              if (signal.contract === outcomeData.contract) {
                return {
                  ...signal,
                  outcome: outcomeData.outcome,
                  exit_price: outcomeData.exit_price
                };
              }
              return signal;
            }));
            
            // Show outcome notification
            const isWin = outcomeData.outcome === 'WIN';
            toast({
              title: isWin ? "🟢 TARGET HIT!" : "🔴 STOP LOSS HIT!",
              description: `${outcomeData.underlying} ${isWin ? 'reached TP' : 'hit SL'} @ ₹${outcomeData.exit_price}`,
              variant: isWin ? "default" : "destructive",
              duration: 7000
            });
            
            // Update stats if included
            if (outcomeData.updated_stats) {
              setScannerStatus(prev => ({ ...prev, stats: outcomeData.updated_stats }));
            }
            
            console.log('🎯 OUTCOME UPDATE:', outcomeData);
          } else if (data.type === 'stats_update') {
            // 📊 REAL-TIME STATS UPDATE
            setScannerStatus(prev => ({ ...prev, stats: data.data.stats }));
            console.log('📊 STATS UPDATE:', data.data.stats);
          } else if (data.type === 'scanner_update') {
            // Update dashboard data
            if (data.data.signals) setSignals(prev => [...data.data.signals, ...prev]);
            if (data.data.options) setOptions(data.data.options);
            if (data.data.stats) setScannerStatus(prev => ({ ...prev, stats: data.data.stats }));
          }
        } catch (error) {
          console.error('WebSocket message error:', error);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      ws.onclose = () => {
        console.log('WebSocket closed, reconnecting in 3s...');
        setTimeout(connectWebSocket, 3000);
      };
      
      return ws;
    };
    
    let websocket = null;
    if (scannerStatus.is_running) {
      websocket = connectWebSocket();
    }
    
    // Fallback polling for non-critical updates
    const interval = setInterval(() => {
      loadScannerStatus();
      if (!scannerStatus.is_running) {
        loadRecentSignals();
        loadCurrentOptions();
      }
    }, 10000);
    
    return () => {
      clearInterval(interval);
      if (websocket) websocket.close();
    };
  }, [scannerStatus.is_running]);

  const loadConfig = async () => {
    try {
      // 1. First load from localStorage (instant and always preferred)
      const localConfig = localStorage.getItem('trinity_config');
      if (localConfig) {
        const parsedConfig = JSON.parse(localConfig);
        setConfig(prev => ({ ...prev, ...parsedConfig }));
        console.log('✅ Configuration loaded from localStorage');
        
        // Check if this config was recently saved
        const savedTimestamp = localStorage.getItem('trinity_config_saved');
        if (savedTimestamp) {
          const timeDiff = Date.now() - parseInt(savedTimestamp);
          if (timeDiff < 60000) { // Within 1 minute
            console.log('📝 Recent config save detected');
          }
        }
        return; // Use localStorage config, don't override with backend
      }
      
      // 2. Only load from backend if no localStorage config exists
      const response = await axios.get(`${API}/scanner/config`);
      if (response.data && Object.keys(response.data).length > 0) {
        setConfig(prev => ({ ...prev, ...response.data }));
        console.log('✅ Configuration loaded from backend (fallback)');
      }
    } catch (error) {
      console.error("Failed to load config from backend:", error);
      // This is fine - localStorage is our primary source
    }
  };

  const loadScannerStatus = async () => {
    try {
      const response = await axios.get(`${API}/scanner/status`, {
        timeout: 8000 // 8 second timeout
      });
      
      console.log('📊 Scanner status response:', response.data);
      setScannerStatus(response.data);
      
      // Also check if LIVE MODE should be displayed
      if (response.data.is_running) {
        console.log('✅ Scanner is running');
      } else {
        console.log('🔴 Scanner is stopped');
      }
      
    } catch (error) {
      console.error("Failed to load scanner status:", error);
      
      // Set a default error state
      setScannerStatus(prev => ({
        ...prev,
        error_message: "Unable to connect to scanner service"
      }));
    }
  };

  const loadRecentSignals = async () => {
    try {
      console.log('🎯 Loading signals from:', `${API}/scanner/signals`);
      const response = await axios.get(`${API}/scanner/signals`, {
        timeout: 12000 // 12 second timeout for signals
      });
      
      const signalsList = response.data || [];
      console.log('🎯 Signals response:', signalsList.length, 'signals loaded');
      
      // Update signals
      setSignals(signalsList);
      
      // 🎯 FORCE STATS UPDATE: Always calculate from actual loaded signals
      const calculatedStats = calculateStatsFromSignals(signalsList);
      setScannerStatus(prev => ({
        ...prev,
        stats: calculatedStats
      }));
      
      console.log('📊 Stats FORCED update from signals:', calculatedStats);
      
      // If no signals, force stats to zero
      if (signalsList.length === 0) {
        setScannerStatus(prev => ({
          ...prev,
          stats: { total: 0, hit: 0, flop: 0, pnl: 0.0 }
        }));
        console.log('📊 Forced stats to ZERO - no signals');
      }
      
    } catch (error) {
      console.error("Failed to load signals:", error);
      // On error, force stats to zero
      setScannerStatus(prev => ({
        ...prev,
        stats: { total: 0, hit: 0, flop: 0, pnl: 0.0 }
      }));
    }
  };

  const loadCurrentOptions = async () => {
    try {
      console.log('📋 Loading options from:', `${API}/scanner/options`);
      const response = await axios.get(`${API}/scanner/options`, {
        timeout: 15000 // 15 second timeout for options
      });
      
      console.log('📋 Options response:', response.data?.length, 'options loaded');
      setOptions(response.data || []);
    } catch (error) {
      console.error("Failed to load options:", error);
      // Set empty array on error to show empty state
      setOptions([]);
    }
  };

  const saveConfig = () => {
    // 🚀 INSTANT SAVE - No backend delays, no async operations
    setSaveStatus('saving');
    setLoading(true);
    
    // Immediate localStorage save (happens instantly)
    localStorage.setItem('trinity_config', JSON.stringify(config));
    localStorage.setItem('trinity_config_saved', Date.now().toString()); // Save timestamp
    
    // Instant success feedback (no waiting for backend)
    setTimeout(() => {
      setSaveStatus('saved');
      setLoading(false);
      
      toast({
        title: "✅ Configuration Saved Instantly!",
        description: "All settings saved to browser storage",
        variant: "default",
        duration: 3000
      });
      
      // Optional: Try to sync to backend in background (don't wait for it)
      axios.post(`${API}/scanner/config`, config).catch(() => {
        console.log('Background sync to backend failed - local save is sufficient');
      });
      
    }, 200); // Just 200ms for visual feedback
    
    // Keep saved status much longer 
    setTimeout(() => {
      if (activeTab === 'settings') {
        // Only reset if still on settings tab after a long time
        setSaveStatus('idle');
      }
    }, 600000); // 10 minutes instead of 10 seconds
  };

  const startScanner = async () => {
    setLoading(true);
    
    try {
      console.log('🔄 Starting scanner...');
      
      // Send current config to backend before starting
      const currentConfig = localStorage.getItem('trinity_config');
      if (currentConfig) {
        try {
          await axios.post(`${API}/scanner/config`, JSON.parse(currentConfig), {
            timeout: 10000 // 10 second timeout
          });
          console.log('📤 Synced config to backend before starting scanner');
        } catch (syncError) {
          console.warn('Config sync failed, but continuing with scanner start:', syncError);
        }
      }
      
      // Start the scanner with timeout
      const response = await axios.post(`${API}/scanner/start`, {}, {
        timeout: 15000 // 15 second timeout
      });
      
      console.log('✅ Scanner start response:', response.status);
      
      // Force reload status immediately
      setTimeout(() => {
        loadScannerStatus();
      }, 1000);
      
      // Show success notification
      toast({
        title: "🚀 Scanner Started!",
        description: "Trinity Wealth Scanner is now running",
        variant: "default",
        duration: 4000
      });
      
    } catch (error) {
      console.error('❌ Scanner start error:', error);
      
      // Simplified error handling - no timeout messages
      if (!error.message.includes('timeout')) {
        toast({
          title: "❌ Start Failed", 
          description: error.response?.data?.detail || "Failed to start scanner",
          variant: "destructive",
          duration: 3000
        });
      }
      // Skip timeout messages - they're not helpful
    } finally {
      setLoading(false);
      
      // Always reload status after attempt
      setTimeout(() => {
        loadScannerStatus();
      }, 2000);
    }
  };

  const stopScanner = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/scanner/stop`);
      toast({
        title: "Success",
        description: "Scanner stopped successfully!",
        variant: "default"
      });
      loadScannerStatus();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to stop scanner",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return "N/A";
    try {
      // Robust IST datetime formatting
      let date;
      
      // Handle different date formats
      if (typeof dateStr === 'string') {
        // Handle ISO strings with or without timezone
        if (dateStr.includes('T')) {
          date = new Date(dateStr);
        } else {
          // Assume IST if no timezone info
          date = new Date(dateStr + '+05:30');
        }
      } else if (dateStr instanceof Date) {
        date = dateStr;
      } else {
        return "N/A";
      }
      
      // Force IST display with proper formatting
      return date.toLocaleString('en-IN', { 
        timeZone: 'Asia/Kolkata',
        year: 'numeric',
        month: '2-digit', 
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false  // 24-hour format
      });
    } catch (error) {
      console.error('Date formatting error:', error, dateStr);
      return "N/A";
    }
  };

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return "N/A";
    return `₹${parseFloat(value).toFixed(2)}`;
  };

  const getOutcomeBadge = (outcome) => {
    switch (outcome?.toLowerCase()) {
      case "win":
        return <Badge variant="default" className="bg-green-500">Win</Badge>;
      case "loss":
        return <Badge variant="destructive">Loss</Badge>;
      case "both":
        return <Badge variant="secondary">Both</Badge>;
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Trinity Wealth Scanner</h1>
            <p className="text-gray-600">Real-time Options Trading Signals Dashboard</p>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Activity className={`w-4 h-4 ${scannerStatus.is_running ? 'text-green-500' : 'text-gray-400'}`} />
              <span className={`text-sm font-medium ${scannerStatus.is_running ? 'text-green-600' : 'text-gray-500'}`}>
                {scannerStatus.is_running ? 'Running' : 'Stopped'}
              </span>
              {scannerStatus.is_running && (
                <div className="flex items-center space-x-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-xs text-green-600 font-medium">LIVE</span>
                </div>
              )}
            </div>
            
            <div className="flex items-center space-x-2">
              <Button
                onClick={scannerStatus.is_running ? stopScanner : startScanner}
                disabled={loading}
                variant={scannerStatus.is_running ? "destructive" : "default"}
                size="sm"
                data-testid={scannerStatus.is_running ? "stop-scanner-btn" : "start-scanner-btn"}
                className={loading ? "opacity-75" : ""}
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 mr-2 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    {scannerStatus.is_running ? "Stopping..." : "Starting..."}
                  </>
                ) : scannerStatus.is_running ? (
                  <>
                    <Square className="w-4 h-4 mr-2" />
                    Stop Scanner
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Start Scanner
                  </>
                )}
              </Button>
              
              <Button
                onClick={() => {
                  loadScannerStatus();
                  loadRecentSignals();
                  loadCurrentOptions();
                }}
                variant="outline"
                size="sm"
                disabled={loading}
                title="Refresh All Data"
              >
                <Activity className="w-4 h-4" />
              </Button>
              
              <Button
                onClick={() => {
                  const stats = calculateStatsFromSignals(signals);
                  setScannerStatus(prev => ({ ...prev, stats }));
                  console.log('🔄 Manual stats refresh:', stats);
                }}
                variant="outline"
                size="sm"
                title="Refresh Stats"
              >
                📊
              </Button>
              
              <Button
                onClick={() => {
                  // Force clear all data
                  setSignals([]);
                  setScannerStatus(prev => ({
                    ...prev,
                    stats: { total: 0, hit: 0, flop: 0, pnl: 0.0 }
                  }));
                  setOptions([]);
                  console.log('🧹 All data cleared manually');
                }}
                variant="outline"
                size="sm"
                title="Clear All Data"
                className="text-red-600 hover:text-red-700"
              >
                🧹
              </Button>
            </div>
          </div>
        </div>

        {/* Date/Time Row - Always Show with LIVE MODE when running */}
        <div className="bg-white border border-gray-300 rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="text-left">
              <div className="text-lg font-semibold text-gray-800">
                {currentTime.toLocaleDateString('en-IN', {
                  timeZone: 'Asia/Kolkata',
                  weekday: 'long',
                  year: 'numeric', 
                  month: 'long',
                  day: 'numeric'
                })}
              </div>
              <div className="text-md font-mono text-gray-600">
                {currentTime.toLocaleTimeString('en-IN', {
                  timeZone: 'Asia/Kolkata',
                  hour12: false,
                  hour: '2-digit',
                  minute: '2-digit', 
                  second: '2-digit'
                })} IST
              </div>
            </div>
            <div className="text-right">
              {scannerStatus.is_running ? (
                <h1 className="text-2xl font-black text-black tracking-wide">✅ LIVE MODE</h1>
              ) : (
                <h1 className="text-2xl font-black text-gray-500 tracking-wide">🔴 OFFLINE</h1>
              )}
            </div>
          </div>
        </div>
        
        {/* Error Alert - only for critical connection errors, not routine status */}
        {scannerStatus.error_message && 
         !scannerStatus.error_message.includes("Unable to connect") &&
         !scannerStatus.error_message.includes("LIVE MODE") && (
          <Alert variant="destructive" data-testid="error-alert">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{scannerStatus.error_message}</AlertDescription>
          </Alert>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Signals</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold" data-testid="total-signals">{scannerStatus.stats?.total || 0}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Winning Signals</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600" data-testid="winning-signals">{scannerStatus.stats?.hit || 0}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Losing Signals</CardTitle>
              <AlertCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600" data-testid="losing-signals">{scannerStatus.stats?.flop || 0}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${(scannerStatus.stats?.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`} data-testid="total-pnl">
                {formatCurrency(scannerStatus.stats?.pnl || 0)}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="dashboard" data-testid="dashboard-tab">Dashboard</TabsTrigger>
            <TabsTrigger value="signals" data-testid="signals-tab">Signals</TabsTrigger>
            <TabsTrigger value="options" data-testid="options-tab">Options</TabsTrigger>
            <TabsTrigger value="settings" data-testid="settings-tab">Settings</TabsTrigger>
          </TabsList>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Recent Signals */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <span>Recent Signals</span>
                    {scannerStatus.is_running && (
                      <div className="flex items-center space-x-1 ml-2">
                        <div className="w-2 h-2 bg-red-500 rounded-full animate-ping"></div>
                        <span className="text-xs text-red-600 font-bold">LIVE</span>
                      </div>
                    )}
                  </CardTitle>
                  <CardDescription>
                    Latest trading signals • {config.allow_intrabar ? '🔥 Intrabar Mode' : '📊 Candle Close Mode'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {signals.slice(0, 5).map((signal) => (
                      <div key={signal.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <div className="font-medium">{signal.underlying} - {signal.contract}</div>
                          <div className="text-sm text-gray-600">Entry: {formatCurrency(signal.entry_price)}</div>
                        </div>
                        <div className="text-right">
                          {getOutcomeBadge(signal.outcome)}
                          <div className="text-xs text-gray-500 mt-1">
                            {formatDateTime(signal.signal_time)}
                          </div>
                        </div>
                      </div>
                    ))}
                    {signals.length === 0 && (
                      <div className="text-center text-gray-500 py-8">
                        No signals generated yet. Start the scanner to begin monitoring.
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* ATM Options Table */}
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>ATM Options Contracts</CardTitle>
                  <CardDescription>At-the-money options being monitored with live data</CardDescription>
                </CardHeader>
                <CardContent>
                  {options.length > 0 ? (
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Underlying</TableHead>
                            <TableHead>Symbol</TableHead>
                            <TableHead>Strike</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>LTP</TableHead>
                            <TableHead>Volume</TableHead>
                            <TableHead>OI</TableHead>
                            <TableHead>Investment</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {options.slice(0, 10).map((option, index) => (
                            <TableRow key={index}>
                              <TableCell className="font-medium">{option.underlying}</TableCell>
                              <TableCell className="text-xs font-mono">{option.symbol}</TableCell>
                              <TableCell>{option.strike}</TableCell>
                              <TableCell>
                                <Badge variant={option.type === 'CE' ? 'default' : 'secondary'}>
                                  {option.type}
                                </Badge>
                              </TableCell>
                              <TableCell className="font-medium">{formatCurrency(option.ltp)}</TableCell>
                              <TableCell>{option.volume?.toLocaleString()}</TableCell>
                              <TableCell>{option.oi?.toLocaleString() || "N/A"}</TableCell>
                              <TableCell className="text-green-600 font-medium">
                                {formatCurrency(option.investment)}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  ) : (
                    <div className="text-center text-gray-500 py-8">
                      <Activity className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                      <p>No ATM options data available</p>
                      <p className="text-sm">Start the scanner to load live contract data</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Signals Tab */}
          <TabsContent value="signals">
            <Card>
              <CardHeader>
                <CardTitle>All Signals</CardTitle>
                <CardDescription>Complete list of generated trading signals</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>Underlying</TableHead>
                      <TableHead>Contract</TableHead>
                      <TableHead>Entry</TableHead>
                      <TableHead>SL</TableHead>
                      <TableHead>TP</TableHead>
                      <TableHead>R:R</TableHead>
                      <TableHead>Lot</TableHead>
                      <TableHead>Outcome</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {signals.map((signal) => (
                      <TableRow key={signal.id}>
                        <TableCell className="text-xs">{formatDateTime(signal.signal_time)}</TableCell>
                        <TableCell>{signal.underlying}</TableCell>
                        <TableCell className="text-xs">{signal.contract}</TableCell>
                        <TableCell>{formatCurrency(signal.entry_price)}</TableCell>
                        <TableCell>{formatCurrency(signal.sl)}</TableCell>
                        <TableCell>{formatCurrency(signal.tp)}</TableCell>
                        <TableCell>{signal.rr ? `1:${signal.rr}` : "N/A"}</TableCell>
                        <TableCell>{signal.lot}</TableCell>
                        <TableCell>{getOutcomeBadge(signal.outcome)}</TableCell>
                      </TableRow>
                    ))}
                    {signals.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={9} className="text-center text-gray-500 py-8">
                          No signals available
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Options Tab */}
          <TabsContent value="options">
            <Card>
              <CardHeader>
                <CardTitle>ATM Options</CardTitle>
                <CardDescription>Current at-the-money options being scanned</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Underlying</TableHead>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Strike</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Expiry</TableHead>
                      <TableHead>LTP</TableHead>
                      <TableHead>Volume</TableHead>
                      <TableHead>OI</TableHead>
                      <TableHead>Investment</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {options.map((option, index) => (
                      <TableRow key={index}>
                        <TableCell>{option.underlying}</TableCell>
                        <TableCell className="text-xs">{option.symbol}</TableCell>
                        <TableCell>{option.strike}</TableCell>
                        <TableCell>
                          <Badge variant={option.type === 'CE' ? 'default' : 'secondary'}>
                            {option.type}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs">{option.expiry}</TableCell>
                        <TableCell>{formatCurrency(option.ltp)}</TableCell>
                        <TableCell>{option.volume?.toLocaleString()}</TableCell>
                        <TableCell>{option.oi?.toLocaleString() || "N/A"}</TableCell>
                        <TableCell>{formatCurrency(option.investment)}</TableCell>
                      </TableRow>
                    ))}
                    {options.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={9} className="text-center text-gray-500 py-8">
                          No options data available
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* API Configuration */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>API Configuration</span>
                    {saveStatus === 'saved' && (
                      <Badge variant="default" className="bg-green-500 text-white animate-pulse">
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        Saved & Active
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription>
                    Kite Connect API credentials
                    {localStorage.getItem('trinity_config') && (
                      <div className="flex items-center mt-1">
                        <span className="text-green-600 text-xs">• Config loaded from storage</span>
                        {localStorage.getItem('trinity_config_saved') && (
                          <span className="text-green-700 text-xs ml-2 font-medium">
                            • Last saved: {new Date(parseInt(localStorage.getItem('trinity_config_saved'))).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>API Key</Label>
                    <Input
                      type="text"
                      value="jdhb0gprnxjr1k31"
                      disabled
                      className="bg-gray-100 text-gray-600"
                    />
                    <div className="text-xs text-gray-500 mt-1">API credentials configured</div>
                  </div>
                  
                  <div>
                    <Label>API Secret</Label>
                    <Input
                      type="password"
                      value="4qnsimdyhlrgm3tqk7toiosu8u2i9wsg"
                      disabled
                      className="bg-gray-100 text-gray-600"
                    />
                    <div className="text-xs text-gray-500 mt-1">API credentials configured</div>
                  </div>
                  
                  <div>
                    <Label htmlFor="access_token">Access Token (Daily)</Label>
                    <Input
                      id="access_token"
                      type="text"
                      value={config.access_token}
                      onChange={(e) => setConfig(prev => ({ ...prev, access_token: e.target.value }))}
                      placeholder="Enter access token (valid for today only)"
                      data-testid="access-token-input"
                    />
                    <div className="text-xs text-gray-500 mt-1">
                      Access token expires at end of trading day - enter once per day
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Trading Settings */}
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>Trading Settings</span>
                    {saveStatus === 'saved' && (
                      <Badge variant="default" className="bg-green-500 text-white">
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        Configuration Saved
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription>Configure trading parameters and expiry dates</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div>
                      <Label htmlFor="mode">Mode</Label>
                      <Select value={config.mode} onValueChange={(value) => setConfig(prev => ({ ...prev, mode: value }))}>
                        <SelectTrigger data-testid="mode-select">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="live">Live Trading</SelectItem>
                          <SelectItem value="backtest">Backtest</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="flex items-center space-x-2 lg:col-span-2 lg:justify-start lg:pt-7">
                      <Switch
                        id="real_trading"
                        checked={config.real_trading}
                        onCheckedChange={(checked) => setConfig(prev => ({ ...prev, real_trading: checked }))}
                        data-testid="real-trading-switch"
                      />
                      <Label htmlFor="real_trading">Enable Real Trading</Label>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div>
                      <Label htmlFor="sl_pct">Stop Loss %</Label>
                      <Input
                        id="sl_pct"
                        type="number"
                        step="0.1"
                        min="0"
                        value={config.sl_pct}
                        onChange={(e) => setConfig(prev => ({ ...prev, sl_pct: parseFloat(e.target.value) }))}
                        data-testid="sl-pct-input"
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="tp_pct">Take Profit %</Label>
                      <Input
                        id="tp_pct"
                        type="number"
                        step="0.1"
                        min="0"
                        value={config.tp_pct}
                        onChange={(e) => setConfig(prev => ({ ...prev, tp_pct: parseFloat(e.target.value) }))}
                        data-testid="tp-pct-input"
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="min_volume">Min Volume</Label>
                      <Input
                        id="min_volume"
                        type="number"
                        min="0"
                        value={config.min_volume}
                        onChange={(e) => setConfig(prev => ({ ...prev, min_volume: parseInt(e.target.value) }))}
                        data-testid="min-volume-input"
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="max_candidates">Max Candidates</Label>
                      <Input
                        id="max_candidates"
                        type="number"
                        min="0"
                        value={config.max_candidates}
                        onChange={(e) => setConfig(prev => ({ ...prev, max_candidates: parseInt(e.target.value) }))}
                        data-testid="max-candidates-input"
                      />
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="min_strike">Min Strike</Label>
                      <Input
                        id="min_strike"
                        type="number"
                        min="100"
                        step="100"
                        value={config.min_strike}
                        onChange={(e) => setConfig(prev => ({ ...prev, min_strike: parseInt(e.target.value) }))}
                        data-testid="min-strike-input"
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="refresh_sec">Refresh Interval (sec)</Label>
                      <Input
                        id="refresh_sec"
                        type="number"
                        min="5"
                        value={config.refresh_sec}
                        onChange={(e) => setConfig(prev => ({ ...prev, refresh_sec: parseInt(e.target.value) }))}
                        data-testid="refresh-interval-input"
                      />
                    </div>
                  </div>
                  
                  <div className="border-t pt-4">
                    <ExpiryDateSelector
                      value={config.only_expiry_dates || []}
                      onChange={(dates) => setConfig(prev => ({ ...prev, only_expiry_dates: dates }))}
                      data-testid="expiry-date-selector"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Telegram Settings */}
              <Card>
                <CardHeader>
                  <CardTitle>Telegram Notifications</CardTitle>
                  <CardDescription>Configure Telegram alerts</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="telegram_enabled"
                      checked={config.telegram_enabled}
                      onCheckedChange={(checked) => setConfig(prev => ({ ...prev, telegram_enabled: checked }))}
                      data-testid="telegram-switch"
                    />
                    <Label htmlFor="telegram_enabled">Enable Telegram Notifications</Label>
                  </div>
                  
                  {config.telegram_enabled && (
                    <>
                      <div>
                        <Label htmlFor="telegram_bot_token">Bot Token</Label>
                        <Input
                          id="telegram_bot_token"
                          type="text"
                          value={config.telegram_bot_token}
                          onChange={(e) => setConfig(prev => ({ ...prev, telegram_bot_token: e.target.value }))}
                          placeholder="Enter your Telegram bot token"
                          data-testid="telegram-bot-token-input"
                        />
                      </div>
                      
                      <div>
                        <Label htmlFor="telegram_chat_id">Chat ID</Label>
                        <Input
                          id="telegram_chat_id"
                          type="text"
                          value={config.telegram_chat_id}
                          onChange={(e) => setConfig(prev => ({ ...prev, telegram_chat_id: e.target.value }))}
                          placeholder="Enter your Telegram chat ID"
                          data-testid="telegram-chat-id-input"
                        />
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>

              {/* Advanced Settings */}
              <Card>
                <CardHeader>
                  <CardTitle>Advanced Settings</CardTitle>
                  <CardDescription>Advanced scanner configuration</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="underlyings">Underlyings (comma-separated)</Label>
                    <Textarea
                      id="underlyings"
                      value={config.underlyings?.join(', ') || ''}
                      onChange={(e) => setConfig(prev => ({ 
                        ...prev, 
                        underlyings: e.target.value.split(',').map(s => s.trim()).filter(s => s) 
                      }))}
                      placeholder="NIFTY, BANKNIFTY, FINNIFTY (leave empty for all)"
                      data-testid="underlyings-input"
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="atm_range">ATM Range</Label>
                    <Input
                      id="atm_range"
                      type="number"
                      min="1"
                      value={config.atm_range}
                      onChange={(e) => setConfig(prev => ({ ...prev, atm_range: parseInt(e.target.value) }))}
                      data-testid="atm-range-input"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="allow_intrabar"
                        checked={config.allow_intrabar}
                        onCheckedChange={(checked) => setConfig(prev => ({ ...prev, allow_intrabar: checked }))}
                        data-testid="intrabar-switch"
                      />
                      <Label htmlFor="allow_intrabar" className="font-medium">Allow Intrabar Analysis</Label>
                    </div>
                    <div className="text-xs text-gray-600 ml-6">
                      {config.allow_intrabar ? (
                        <span className="text-orange-600 font-medium">🔥 ON: Signals generated immediately when POI price is hit (real-time)</span>
                      ) : (
                        <span className="text-blue-600 font-medium">📊 OFF: Wait for 15-minute candle close before generating signals</span>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Save Button */}
            <div className="flex justify-end">
              <Button 
                onClick={saveConfig} 
                data-testid="save-config-btn"
                disabled={saveStatus === 'saving'}
                className={`
                  ${saveStatus === 'saving' ? 'bg-yellow-500 hover:bg-yellow-600' : ''}
                  ${saveStatus === 'saved' ? 'bg-green-600 hover:bg-green-700' : ''}
                  ${saveStatus === 'error' ? 'bg-red-600 hover:bg-red-700' : ''}
                `}
              >
                {saveStatus === 'saving' && (
                  <>
                    <div className="w-4 h-4 mr-2 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    Saving...
                  </>
                )}
                {saveStatus === 'saved' && (
                  <>
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    ✅ Saved Successfully!
                  </>
                )}
                {saveStatus === 'error' && (
                  <>
                    <AlertCircle className="w-4 h-4 mr-2" />
                    Save Failed
                  </>
                )}
                {saveStatus === 'idle' && (
                  <>
                    <Settings className="w-4 h-4 mr-2" />
                    Save Configuration
                  </>
                )}
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </div>
      
      <Toaster />
    </div>
  );
}

export default App;
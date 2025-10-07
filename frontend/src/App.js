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
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [config, setConfig] = useState({
    api_key: "",
    api_secret: "",
    access_token: "",
    real_trading: false,
    telegram_enabled: false,
    telegram_bot_token: "",
    telegram_chat_id: "",
    atm_range: 1,
    min_volume: 1000,
    min_strike: 1000,
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
  
  const [signals, setSignals] = useState([]);
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("dashboard");
  const { toast } = useToast();

  // Load configuration on component mount
  useEffect(() => {
    loadConfig();
    loadScannerStatus();
    loadRecentSignals();
    loadCurrentOptions();
    
    // Set up polling for real-time updates
    const interval = setInterval(() => {
      loadScannerStatus();
      if (scannerStatus.is_running) {
        loadRecentSignals();
        loadCurrentOptions();
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [scannerStatus.is_running]);

  const loadConfig = async () => {
    try {
      const response = await axios.get(`${API}/scanner/config`);
      if (response.data) {
        setConfig(prev => ({ ...prev, ...response.data }));
      }
    } catch (error) {
      console.error("Failed to load config:", error);
    }
  };

  const loadScannerStatus = async () => {
    try {
      const response = await axios.get(`${API}/scanner/status`);
      setScannerStatus(response.data);
    } catch (error) {
      console.error("Failed to load scanner status:", error);
    }
  };

  const loadRecentSignals = async () => {
    try {
      const response = await axios.get(`${API}/scanner/signals`);
      setSignals(response.data || []);
    } catch (error) {
      console.error("Failed to load signals:", error);
    }
  };

  const loadCurrentOptions = async () => {
    try {
      const response = await axios.get(`${API}/scanner/options`);
      setOptions(response.data || []);
    } catch (error) {
      console.error("Failed to load options:", error);
    }
  };

  const saveConfig = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/scanner/config`, config);
      toast({
        title: "Success",
        description: "Configuration saved successfully!",
        variant: "default"
      });
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to save configuration",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const startScanner = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/scanner/start`);
      toast({
        title: "Success",
        description: "Scanner started successfully!",
        variant: "default"
      });
      loadScannerStatus();
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to start scanner",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
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
      return new Date(dateStr).toLocaleString();
    } catch {
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
            </div>
            
            <Button
              onClick={scannerStatus.is_running ? stopScanner : startScanner}
              disabled={loading}
              variant={scannerStatus.is_running ? "destructive" : "default"}
              size="sm"
              data-testid={scannerStatus.is_running ? "stop-scanner-btn" : "start-scanner-btn"}
            >
              {scannerStatus.is_running ? (
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
          </div>
        </div>

        {/* Error Alert */}
        {scannerStatus.error_message && (
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
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recent Signals */}
              <Card>
                <CardHeader>
                  <CardTitle>Recent Signals</CardTitle>
                  <CardDescription>Latest trading signals generated</CardDescription>
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

              {/* Top Options */}
              <Card>
                <CardHeader>
                  <CardTitle>Top ATM Options</CardTitle>
                  <CardDescription>High volume options being monitored</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {options.slice(0, 5).map((option, index) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <div className="font-medium">{option.underlying} {option.strike} {option.type}</div>
                          <div className="text-sm text-gray-600">LTP: {formatCurrency(option.ltp)}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm">Vol: {option.volume?.toLocaleString()}</div>
                          <div className="text-xs text-gray-500">Lot: {option.lot}</div>
                        </div>
                      </div>
                    ))}
                    {options.length === 0 && (
                      <div className="text-center text-gray-500 py-8">
                        No options data available. Start the scanner to load data.
                      </div>
                    )}
                  </div>
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
                  <CardTitle>API Configuration</CardTitle>
                  <CardDescription>Kite Connect API credentials</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="api_key">API Key</Label>
                    <Input
                      id="api_key"
                      type="text"
                      value={config.api_key}
                      onChange={(e) => setConfig(prev => ({ ...prev, api_key: e.target.value }))}
                      placeholder="Enter your Kite API key"
                      data-testid="api-key-input"
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="api_secret">API Secret</Label>
                    <Input
                      id="api_secret"
                      type="password"
                      value={config.api_secret}
                      onChange={(e) => setConfig(prev => ({ ...prev, api_secret: e.target.value }))}
                      placeholder="Enter your Kite API secret"
                      data-testid="api-secret-input"
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="access_token">Access Token (Optional)</Label>
                    <Input
                      id="access_token"
                      type="text"
                      value={config.access_token}
                      onChange={(e) => setConfig(prev => ({ ...prev, access_token: e.target.value }))}
                      placeholder="Will be auto-generated if empty"
                      data-testid="access-token-input"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Trading Settings */}
              <Card>
                <CardHeader>
                  <CardTitle>Trading Settings</CardTitle>
                  <CardDescription>Configure trading parameters</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
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
                  
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="real_trading"
                      checked={config.real_trading}
                      onCheckedChange={(checked) => setConfig(prev => ({ ...prev, real_trading: checked }))}
                      data-testid="real-trading-switch"
                    />
                    <Label htmlFor="real_trading">Enable Real Trading</Label>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
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
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
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
                  
                  <div className="grid grid-cols-2 gap-4">
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
                  
                  <div className="flex items-center space-x-2">
                    <Switch
                      id="allow_intrabar"
                      checked={config.allow_intrabar}
                      onCheckedChange={(checked) => setConfig(prev => ({ ...prev, allow_intrabar: checked }))}
                      data-testid="intrabar-switch"
                    />
                    <Label htmlFor="allow_intrabar">Allow Intrabar Analysis</Label>
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Save Button */}
            <div className="flex justify-end">
              <Button onClick={saveConfig} disabled={loading} data-testid="save-config-btn">
                <Settings className="w-4 h-4 mr-2" />
                {loading ? 'Saving...' : 'Save Configuration'}
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
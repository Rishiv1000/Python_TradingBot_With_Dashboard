import { useState, useEffect, useCallback, useRef } from "react";
import api from "./api";
import Sidebar from "./components/Sidebar";
import StrategyCards from "./components/StrategyCards";
import LiveDFTab from "./components/tabs/LiveDFTab";
import SymbolsTab from "./components/tabs/SymbolsTab";
import PositionsTab from "./components/tabs/PositionsTab";
import HistoryTab from "./components/tabs/HistoryTab";
import TerminalTab from "./components/tabs/TerminalTab";
import BacktestTab from "./components/tabs/BacktestTab";
import "./App.css";

const TABS = [
  { id: "livedf",    label: "📊 Live DF" },
  { id: "backtest",  label: "🔬 Backtest" },
  { id: "symbols",   label: "📋 Symbols" },
  { id: "positions", label: "📂 Positions" },
  { id: "history",   label: "📜 History" },
  { id: "terminal",  label: "🖥️ Terminal" },
];

export default function App() {
  const [status, setStatus]           = useState(null);
  const [kiteLoggedIn, setKiteLoggedIn] = useState(false);
  const [activeTab, setActiveTab]     = useState("livedf");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(5);
  const [lastSync, setLastSync]       = useState("");
  const [symbolsCache, setSymbolsCache] = useState({});

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.get("/api/status");
      setStatus(res.data);
      setLastSync(new Date().toLocaleTimeString());
    } catch {}
  }, []);

  const fetchKiteStatus = useCallback(async () => {
    try {
      const res = await api.get("/api/kite/status");
      setKiteLoggedIn(res.data.logged_in);
    } catch { setKiteLoggedIn(false); }
  }, []);

  const fetchAllSymbols = useCallback(async () => {
    try {
      const strategies = ["GREEN", "GREEN3"];
      const results = await Promise.all(strategies.map(s => api.get(`/api/symbols/${s}`).then(r => [s, r.data])));
      const cache = {};
      results.forEach(([s, data]) => { cache[s] = data; });
      setSymbolsCache(cache);
    } catch {}
  }, []);

  const refreshSymbols = useCallback(async (strategy) => {
    try {
      const res = await api.get(`/api/symbols/${strategy}`);
      setSymbolsCache(prev => ({ ...prev, [strategy]: res.data }));
    } catch {}
  }, []);

  useEffect(() => {
    fetchKiteStatus();
    fetchStatus();
    fetchAllSymbols();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchStatus, refreshInterval * 1000);
    return () => clearInterval(id);
  }, [autoRefresh, refreshInterval, fetchStatus]);

  const handleRefresh = useCallback(() => { fetchStatus(); fetchAllSymbols(); }, [fetchStatus, fetchAllSymbols]);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar
        status={status}
        kiteLoggedIn={kiteLoggedIn}
        autoRefresh={autoRefresh}
        setAutoRefresh={setAutoRefresh}
        refreshInterval={refreshInterval}
        setRefreshInterval={setRefreshInterval}
        lastSync={lastSync}
        onRefresh={handleRefresh}
        onSessionSaved={fetchKiteStatus}
      />

      <div style={{ marginLeft: "260px", flex: 1, padding: "24px 28px", minWidth: 0 }}>
        <div style={{ marginBottom: "20px" }}>
          <h1 style={{ fontSize: "22px", fontWeight: 800, color: "#f0f6fc", margin: 0 }}>🧪 Multi-Strategy Backtest Lab</h1>
        </div>

        <StrategyCards status={status} />

        <div className="tab-bar">
          {TABS.map(tab => (
            <button key={tab.id} className={`tab-btn${activeTab === tab.id ? " active" : ""}`} onClick={() => setActiveTab(tab.id)}>
              {tab.label}
            </button>
          ))}
        </div>

        <div style={{ display: activeTab === "livedf"    ? "block" : "none" }}><LiveDFTab    symbolsCache={symbolsCache} status={status} /></div>
        <div style={{ display: activeTab === "backtest"  ? "block" : "none" }}><BacktestTab  status={status} /></div>
        <div style={{ display: activeTab === "symbols"   ? "block" : "none" }}><SymbolsTab   symbolsCache={symbolsCache} status={status} onRefreshSymbols={refreshSymbols} /></div>
        <div style={{ display: activeTab === "positions" ? "block" : "none" }}><PositionsTab /></div>
        <div style={{ display: activeTab === "history"   ? "block" : "none" }}><HistoryTab   /></div>
        <div style={{ display: activeTab === "terminal"  ? "block" : "none" }}><TerminalTab  status={status} /></div>
      </div>
    </div>
  );
}

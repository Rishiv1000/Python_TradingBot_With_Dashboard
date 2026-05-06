import { useState, useEffect, useCallback, useRef } from "react";
import api from "./api";
import Sidebar from "./components/Sidebar";
import StrategyCards from "./components/StrategyCards";
import SymbolsTab from "./components/tabs/SymbolsTab";
import LiveDFTab from "./components/tabs/LiveDFTab";
import PositionsTab from "./components/tabs/PositionsTab";
import HistoryTab from "./components/tabs/HistoryTab";
import TerminalTab from "./components/tabs/TerminalTab";

const TABS = [
 
  { id: "livedf",    label: "📊 Live DF" },
  { id: "positions", label: "📂 Positions" },
  { id: "history",   label: "📜 History" },
  { id: "terminal",  label: "🖥️ Terminal" },
   { id: "symbols",   label: "📋 Symbols" },
];

export default function App() {
  // ── core state ──────────────────────────────────────────────────────────────
  const [status, setStatus]           = useState(null);
  const [kiteLoggedIn, setKiteLoggedIn] = useState(false);
  const [activeTab, setActiveTab]     = useState("livedf");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(5);
  const [lastSync, setLastSync]       = useState("");

  // ── symbols cache — fetched once, updated on add/delete ───────────────────
  // { GREEN: [...], RSI: [...] }
  const [symbolsCache, setSymbolsCache] = useState({});
  const symbolsFetched = useRef(false);

  // ── fetch strategy running status only (fast, no network to Kite) ─────────
  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.get("/api/status");
      setStatus(res.data);
      setLastSync(new Date().toLocaleTimeString());
    } catch {
      // API not running yet
    }
  }, []);

  // ── fetch kite login status — only once on mount, and after session save ──
  const fetchKiteStatus = useCallback(async () => {
    try {
      const res = await api.get("/api/kite/status");
      setKiteLoggedIn(res.data.logged_in);
    } catch {
      setKiteLoggedIn(false);
    }
  }, []);

  // ── fetch all symbols once ─────────────────────────────────────────────────
  const fetchAllSymbols = useCallback(async () => {
    try {
      const strategies = ["GREEN", "GREEN3"];
      const results = await Promise.all(
        strategies.map((s) => api.get(`/api/symbols/${s}`).then((r) => [s, r.data]))
      );
      const cache = {};
      results.forEach(([s, data]) => { cache[s] = data; });
      setSymbolsCache(cache);
      symbolsFetched.current = true;
    } catch {
      // ignore
    }
  }, []);

  // ── refresh symbols for one strategy (after add/delete) ───────────────────
  const refreshSymbols = useCallback(async (strategy) => {
    try {
      const res = await api.get(`/api/symbols/${strategy}`);
      setSymbolsCache((prev) => ({ ...prev, [strategy]: res.data }));
    } catch {
      // ignore
    }
  }, []);

  // ── on mount: fetch everything once ───────────────────────────────────────
  useEffect(() => {
    fetchKiteStatus();
    fetchStatus();
    fetchAllSymbols();
  }, []);

  // ── auto-refresh: only status (running/stopped counts) ────────────────────
  // kite status and symbols do NOT auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchStatus, refreshInterval * 1000);
    return () => clearInterval(id);
  }, [autoRefresh, refreshInterval, fetchStatus]);

  // ── manual refresh: status + symbols ──────────────────────────────────────
  const handleRefresh = useCallback(() => {
    fetchStatus();
    fetchAllSymbols();
  }, [fetchStatus, fetchAllSymbols]);

  // ── after session saved: re-check kite status ─────────────────────────────
  const handleSessionSaved = useCallback(() => {
    fetchKiteStatus();
  }, [fetchKiteStatus]);

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
        onSessionSaved={handleSessionSaved}
      />

      <div style={{ marginLeft: "260px", flex: 1, padding: "24px 28px", minWidth: 0 }}>
        <div style={{ marginBottom: "20px" }}>
          <h1 style={{ fontSize: "22px", fontWeight: 800, color: "#f0f6fc", margin: 0 }}>
            📡 Multi-Strategy Live Terminal
          </h1>
        </div>

        <StrategyCards status={status} />

        <div className="tab-bar">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tab-btn${activeTab === tab.id ? " active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* All tabs always mounted (display:none when inactive) so state is preserved */}
       
        <div style={{ display: activeTab === "livedf"    ? "block" : "none" }}>
          <LiveDFTab key="livedf" symbolsCache={symbolsCache} status={status} />
        </div>
        <div style={{ display: activeTab === "positions" ? "block" : "none" }}>
          <PositionsTab key="positions" />
        </div>
        <div style={{ display: activeTab === "history"   ? "block" : "none" }}>
          <HistoryTab key="history" />
        </div>
        <div style={{ display: activeTab === "terminal"  ? "block" : "none" }}>
          <TerminalTab key="terminal" status={status} />
        </div>
         <div style={{ display: activeTab === "symbols"   ? "block" : "none" }}>
          <SymbolsTab key="symbols" symbolsCache={symbolsCache} status={status} onRefreshSymbols={refreshSymbols} />
        </div>
      </div>
    </div>
  );
}

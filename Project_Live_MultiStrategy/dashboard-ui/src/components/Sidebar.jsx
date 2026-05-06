import { useState } from "react";
import api from "../api";

const SIDEBAR_STYLE = {
  position: "fixed",
  left: 0,
  top: 0,
  bottom: 0,
  width: "260px",
  background: "#010409",
  borderRight: "1px solid #30363d",
  overflowY: "auto",
  padding: "16px 14px",
  zIndex: 100,
  display: "flex",
  flexDirection: "column",
  gap: "0",
};

export default function Sidebar({
  status,
  kiteLoggedIn,
  autoRefresh,
  setAutoRefresh,
  refreshInterval,
  setRefreshInterval,
  lastSync,
  onRefresh,
  onSessionSaved,
}) {
  const [loginUrl, setLoginUrl] = useState("");
  const [showUrlModal, setShowUrlModal] = useState(false);
  const [requestToken, setRequestToken] = useState("");
  const [sessionMsg, setSessionMsg] = useState("");
  const [sessionLoading, setSessionLoading] = useState(false);

  const handleGetLoginUrl = async () => {
    try {
      const res = await api.get("/api/kite/login_url");
      setLoginUrl(res.data.url);
      setShowUrlModal(true);
    } catch (e) {
      alert("Failed to get login URL: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleGenerateSession = async () => {
    if (!requestToken.trim()) {
      setSessionMsg("Enter a request token first.");
      return;
    }
    setSessionLoading(true);
    setSessionMsg("");
    try {
      const res = await api.post("/api/kite/session", { request_token: requestToken.trim() });
      if (res.data.success) {
        setSessionMsg("✅ Session saved!");
        setRequestToken("");
        onSessionSaved();   // re-check kite status once
        onRefresh();
      } else {
        setSessionMsg("❌ " + (res.data.error || "Unknown error"));
      }
    } catch (e) {
      setSessionMsg("❌ " + (e.response?.data?.detail || e.message));
    } finally {
      setSessionLoading(false);
    }
  };

  const handleStart = async (strategy) => {
    try {
      await api.post(`/api/strategy/${strategy}/start`);
      onRefresh();
    } catch (e) {
      alert("Start failed: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleStop = async (strategy) => {
    try {
      await api.post(`/api/strategy/${strategy}/stop`);
      onRefresh();
    } catch (e) {
      alert("Stop failed: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleTerminate = async (strategy) => {
    try {
      await api.post(`/api/strategy/${strategy}/terminate`);
      onRefresh();
    } catch (e) {
      alert("Terminate failed: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleStopAll = async () => {
    try {
      await api.post("/api/strategy/stop-all");
      onRefresh();
    } catch (e) {
      alert("Stop all failed: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleKillAll = async () => {
    try {
      await api.post("/api/strategy/kill-all");
      onRefresh();
    } catch (e) {
      alert("Kill all failed: " + (e.response?.data?.detail || e.message));
    }
  };

  const [setupDbMsg, setSetupDbMsg]         = useState("");
  const [setupDbLoading, setSetupDbLoading] = useState(false);
  const [defaultsMsg, setDefaultsMsg]       = useState("");
  const [defaultsLoading, setDefaultsLoading] = useState(false);
  const [reloadMsg, setReloadMsg]           = useState("");
  const [reloadLoading, setReloadLoading]   = useState(false);
  const [stopApiMsg, setStopApiMsg]         = useState("");

  const handleSetupDb = async () => {
    setSetupDbLoading(true); setSetupDbMsg("");
    try {
      const res = await api.post("/api/setup-db");
      setSetupDbMsg(res.data.success ? `✅ ${res.data.message}` : `❌ ${res.data.error}`);
    } catch (e) {
      setSetupDbMsg("❌ " + (e.response?.data?.detail || e.message));
    } finally { setSetupDbLoading(false); }
  };

  const handleSetDefaults = async () => {
    setDefaultsLoading(true); setDefaultsMsg("");
    try {
      const res = await api.post("/api/set-defaults");
      setDefaultsMsg(res.data.success ? `✅ ${res.data.updated} tokens updated` : `❌ ${res.data.error}`);
      onRefresh();
    } catch (e) {
      setDefaultsMsg("❌ " + (e.response?.data?.detail || e.message));
    } finally { setDefaultsLoading(false); }
  };

  const handleReloadSymbols = async () => {
    setReloadLoading(true); setReloadMsg("");
    try {
      const res = await api.post("/api/symbols/reload-all");
      setReloadMsg(res.data.success ? "✅ Reload signal sent" : `❌ ${res.data.error}`);
    } catch (e) {
      setReloadMsg("❌ " + (e.response?.data?.detail || e.message));
    } finally { setReloadLoading(false); }
  };

  const handleStopServer = async () => {
    if (!window.confirm("Stop the API server?")) return;
    try {
      await api.post("/api/server/stop");
      setStopApiMsg("✅ Server stopping...");
    } catch {
      setStopApiMsg("✅ Server stopping...");
    }
  };

  return (
    <>
      <div style={SIDEBAR_STYLE}>
        {/* Title */}
        <div style={{ fontSize: "16px", fontWeight: 800, color: "#f0f6fc", marginBottom: "16px" }}>
          📡 Live Terminal
        </div>

        <hr className="divider" />

        {/* Kite Login */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
            🔑 Kite Login
          </div>
          {kiteLoggedIn ? (
            <div style={{ color: "#2ea043", fontWeight: 700, fontSize: "13px", marginBottom: "8px" }}>
              ✅ Session Active
            </div>
          ) : (
            <div style={{ color: "#e3b341", fontWeight: 700, fontSize: "13px", marginBottom: "8px" }}>
              ⚠️ Not Logged In
            </div>
          )}
          <button
            className="btn-blue"
            style={{ width: "100%", marginBottom: "8px" }}
            onClick={handleGetLoginUrl}
          >
            Get Login URL
          </button>
          <input
            type="text"
            placeholder="Paste Request Token"
            value={requestToken}
            onChange={(e) => setRequestToken(e.target.value)}
            style={{ width: "100%", marginBottom: "6px" }}
          />
          <button
            className="btn-primary"
            style={{ width: "100%" }}
            onClick={handleGenerateSession}
            disabled={sessionLoading}
          >
            {sessionLoading ? "Generating..." : "Generate Session"}
          </button>
          {sessionMsg && (
            <div style={{ fontSize: "12px", marginTop: "6px", color: sessionMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>
              {sessionMsg}
            </div>
          )}
        </div>

        <hr className="divider" />

        {/* Strategy Control */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "10px" }}>
            ⚙️ Strategy Control
          </div>

          {status && Object.entries(status).map(([strategy, info]) => {
            const running = info.running;
            const statusColor = running ? "#2ea043" : "#da3633";
            const statusLabel = running ? "RUNNING" : "STOPPED";
            return (
              <div key={strategy} style={{ marginBottom: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                  <span style={{ fontWeight: 800, color: "#f0f6fc", fontSize: "13px" }}>{strategy}</span>
                  <span
                    className="pill"
                    style={{
                      background: statusColor + "22",
                      color: statusColor,
                      border: `1px solid ${statusColor}`,
                    }}
                  >
                    {statusLabel}
                  </span>
                </div>
                <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "6px" }}>
                  Symbols: {info.symbol_count} &nbsp;|&nbsp; Open: {info.open_count}
                </div>
                <div style={{ display: "flex", gap: "4px" }}>
                  <button
                    className="btn-primary btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => handleStart(strategy)}
                    title={`Start ${strategy}`}
                  >
                    ▶
                  </button>
                  <button
                    className="btn-secondary btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => handleStop(strategy)}
                    title={`Stop ${strategy}`}
                  >
                    ■
                  </button>
                  <button
                    className="btn-danger btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => handleTerminate(strategy)}
                    title={`Terminate ${strategy}`}
                  >
                    ✕
                  </button>
                </div>
              </div>
            );
          })}

          <div style={{ display: "flex", gap: "6px", marginTop: "8px" }}>
            <button className="btn-warning" style={{ flex: 1, fontSize: "12px" }} onClick={handleStopAll}>
              ⛔ Stop All
            </button>
            <button className="btn-danger" style={{ flex: 1, fontSize: "12px" }} onClick={handleKillAll}>
              💀 Kill All
            </button>
          </div>
        </div>

        <hr className="divider" />

        {/* Setup */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
            🔧 Setup
          </div>
          <button className="btn-blue" style={{ width: "100%", marginBottom: "6px" }} onClick={handleSetupDb} disabled={setupDbLoading}>
            {setupDbLoading ? "Setting up..." : "🗄️ Setup DB"}
          </button>
          {setupDbMsg && <div style={{ fontSize: "11px", marginBottom: "6px", color: setupDbMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>{setupDbMsg}</div>}
          <button className="btn-secondary" style={{ width: "100%" }} onClick={handleSetDefaults} disabled={defaultsLoading}>
            {defaultsLoading ? "Running..." : "⚙️ Set Defaults"}
          </button>
          <div style={{ fontSize: "11px", color: "#8b949e", marginTop: "4px" }}>Resets positions & fills tokens</div>
          {defaultsMsg && <div style={{ fontSize: "11px", marginTop: "4px", color: defaultsMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>{defaultsMsg}</div>}
        </div>

        <hr className="divider" />

        {/* Auto Refresh */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#8b949e", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "8px" }}>
            🔄 Refresh
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontSize: "13px" }}>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                style={{ width: "auto", padding: 0, border: "none" }}
              />
              Auto-refresh
            </label>
          </div>
          {autoRefresh && (
            <div style={{ marginBottom: "8px" }}>
              <div style={{ fontSize: "12px", color: "#8b949e", marginBottom: "4px" }}>
                Interval: {refreshInterval}s
              </div>
              <input
                type="range"
                min={2}
                max={30}
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                style={{ width: "100%", padding: 0, border: "none", background: "transparent", cursor: "pointer" }}
              />
            </div>
          )}
          <button className="btn-secondary" style={{ width: "100%", fontSize: "12px" }} onClick={onRefresh}>
            Refresh Now
          </button>
        </div>

        <div style={{ fontSize: "11px", color: "#484f58", marginTop: "auto", paddingTop: "8px" }}>
          Last sync: {lastSync || "—"}
        </div>
      </div>

      {/* Login URL Modal */}
      {showUrlModal && (
        <div className="modal-overlay" onClick={() => setShowUrlModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">🔗 Kite Login URL</div>
            <div className="modal-url">{loginUrl}</div>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                className="btn-blue"
                onClick={() => { navigator.clipboard.writeText(loginUrl); }}
              >
                Copy URL
              </button>
              <a href={loginUrl} target="_blank" rel="noreferrer">
                <button className="btn-primary">Open in Browser</button>
              </a>
              <button className="btn-secondary" onClick={() => setShowUrlModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

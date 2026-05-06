import { useState } from "react";
import api from "../api";

export default function Sidebar({ status, kiteLoggedIn, autoRefresh, setAutoRefresh, refreshInterval, setRefreshInterval, lastSync, onRefresh, onSessionSaved }) {
  const [loginUrl, setLoginUrl]       = useState("");
  const [showModal, setShowModal]     = useState(false);
  const [reqToken, setReqToken]       = useState("");
  const [sessionMsg, setSessionMsg]   = useState("");
  const [sessionLoading, setSessionLoading] = useState(false);
  const [defaultsMsg, setDefaultsMsg] = useState("");
  const [defaultsLoading, setDefaultsLoading] = useState(false);

  const handleGetUrl = async () => {
    try {
      const res = await api.get("/api/kite/login_url");
      setLoginUrl(res.data.url);
      setShowModal(true);
    } catch (e) {
      alert("Failed: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleGenSession = async () => {
    if (!reqToken.trim()) { setSessionMsg("Enter request token."); return; }
    setSessionLoading(true); setSessionMsg("");
    try {
      const res = await api.post("/api/kite/session", { request_token: reqToken.trim() });
      if (res.data.success) {
        setSessionMsg("✅ Session saved!"); setReqToken("");
        onSessionSaved(); onRefresh();
      } else {
        setSessionMsg("❌ " + (res.data.error || "Error"));
      }
    } catch (e) {
      setSessionMsg("❌ " + (e.response?.data?.detail || e.message));
    } finally { setSessionLoading(false); }
  };

  const handleSetDefaults = async () => {
    setDefaultsLoading(true); setDefaultsMsg("");
    try {
      const res = await api.post("/api/set-defaults");
      if (res.data.success) {
        setDefaultsMsg(`✅ Done — ${res.data.updated} tokens updated`);
        onRefresh();
      } else {
        setDefaultsMsg("❌ " + (res.data.error || "Error"));
      }
    } catch (e) {
      setDefaultsMsg("❌ " + (e.response?.data?.detail || e.message));
    } finally { setDefaultsLoading(false); }
  };

  const handleStart   = async (s) => { try { await api.post(`/api/strategy/${s}/start`);     onRefresh(); } catch (e) { alert(e.message); } };
  const handleStop    = async (s) => { try { await api.post(`/api/strategy/${s}/stop`);      onRefresh(); } catch (e) { alert(e.message); } };
  const handleTerm    = async (s) => { try { await api.post(`/api/strategy/${s}/terminate`); onRefresh(); } catch (e) { alert(e.message); } };
  const handleStopAll = async ()  => { try { await api.post("/api/strategy/stop-all");       onRefresh(); } catch (e) { alert(e.message); } };
  const handleKillAll = async ()  => { try { await api.post("/api/strategy/kill-all");       onRefresh(); } catch (e) { alert(e.message); } };

  const sliderStyle = {
    width: "100%",
    height: "4px",
    appearance: "none",
    WebkitAppearance: "none",
    background: "#30363d",
    borderRadius: "2px",
    outline: "none",
    cursor: "pointer",
    border: "none",
    padding: 0,
  };

  return (
    <>
      <div style={{ position: "fixed", left: 0, top: 0, bottom: 0, width: "260px", background: "#010409", borderRight: "1px solid #30363d", overflowY: "auto", padding: "16px 14px", zIndex: 100, display: "flex", flexDirection: "column" }}>
        <div style={{ fontSize: "16px", fontWeight: 800, color: "#f0f6fc", marginBottom: "16px" }}>🧪 Backtest Lab</div>
        <hr className="divider" />

        {/* Kite Login */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#8b949e", textTransform: "uppercase", marginBottom: "8px" }}>🔑 Kite Login</div>
          {kiteLoggedIn
            ? <div style={{ color: "#2ea043", fontWeight: 700, fontSize: "13px", marginBottom: "8px" }}>✅ Session Active</div>
            : <div style={{ color: "#e3b341", fontWeight: 700, fontSize: "13px", marginBottom: "8px" }}>⚠️ Not Logged In</div>
          }
          <button className="btn-blue" style={{ width: "100%", marginBottom: "8px" }} onClick={handleGetUrl}>Get Login URL</button>
          <input type="text" placeholder="Paste Request Token" value={reqToken} onChange={e => setReqToken(e.target.value)} style={{ width: "100%", marginBottom: "6px" }} />
          <button className="btn-primary" style={{ width: "100%" }} onClick={handleGenSession} disabled={sessionLoading}>
            {sessionLoading ? "Generating..." : "Generate Session"}
          </button>
          {sessionMsg && <div style={{ fontSize: "12px", marginTop: "6px", color: sessionMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>{sessionMsg}</div>}
        </div>
        <hr className="divider" />

        {/* Set Defaults */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#8b949e", textTransform: "uppercase", marginBottom: "8px" }}>🔧 Setup</div>
          <button
            className="btn-blue"
            style={{ width: "100%" }}
            onClick={handleSetDefaults}
            disabled={defaultsLoading}
          >
            {defaultsLoading ? "Running..." : "⚙️ Set Defaults"}
          </button>
          <div style={{ fontSize: "11px", color: "#8b949e", marginTop: "4px" }}>
            Resets positions & fills missing instrument tokens
          </div>
          {defaultsMsg && (
            <div style={{ fontSize: "12px", marginTop: "6px", color: defaultsMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>
              {defaultsMsg}
            </div>
          )}
        </div>
        <hr className="divider" />

        {/* Strategy Control */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#8b949e", textTransform: "uppercase", marginBottom: "10px" }}>⚙️ Strategy Control</div>
          {status && Object.entries(status).map(([s, info]) => {
            const color = info.running ? "#2ea043" : "#da3633";
            return (
              <div key={s} style={{ marginBottom: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                  <span style={{ fontWeight: 800, color: "#f0f6fc", fontSize: "13px" }}>{s}</span>
                  <span className="pill" style={{ background: color + "22", color, border: `1px solid ${color}` }}>{info.running ? "RUNNING" : "STOPPED"}</span>
                </div>
                <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "6px" }}>Symbols: {info.symbol_count} | Open: {info.open_count}</div>
                <div style={{ display: "flex", gap: "4px" }}>
                  <button className="btn-primary btn-sm" style={{ flex: 1 }} onClick={() => handleStart(s)} title="Start">▶</button>
                  <button className="btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => handleStop(s)} title="Stop">■</button>
                  <button className="btn-danger btn-sm" style={{ flex: 1 }} onClick={() => handleTerm(s)} title="Terminate">✕</button>
                </div>
              </div>
            );
          })}
          <div style={{ display: "flex", gap: "6px", marginTop: "8px" }}>
            <button className="btn-warning" style={{ flex: 1, fontSize: "12px" }} onClick={handleStopAll}>⛔ Stop All</button>
            <button className="btn-danger"  style={{ flex: 1, fontSize: "12px" }} onClick={handleKillAll}>💀 Kill All</button>
          </div>
        </div>
        <hr className="divider" />

        {/* Refresh */}
        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "#8b949e", textTransform: "uppercase", marginBottom: "8px" }}>🔄 Refresh</div>
          <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontSize: "13px", marginBottom: "8px" }}>
            <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} style={{ width: "auto", padding: 0, border: "none" }} />
            Auto-refresh
          </label>
          <button className="btn-secondary" style={{ width: "100%", fontSize: "12px", marginTop: "4px" }} onClick={onRefresh}>Refresh Now</button>
        </div>

        <div style={{ fontSize: "11px", color: "#484f58", marginTop: "auto", paddingTop: "8px" }}>Last sync: {lastSync || "—"}</div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <div className="modal-title">🔗 Kite Login URL</div>
            <div className="modal-url">{loginUrl}</div>
            <div style={{ display: "flex", gap: "8px" }}>
              <button className="btn-blue" onClick={() => navigator.clipboard.writeText(loginUrl)}>Copy URL</button>
              <a href={loginUrl} target="_blank" rel="noreferrer"><button className="btn-primary">Open in Browser</button></a>
              <button className="btn-secondary" onClick={() => setShowModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

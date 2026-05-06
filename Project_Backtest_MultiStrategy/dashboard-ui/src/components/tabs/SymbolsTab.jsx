import { useState } from "react";
import api from "../../api";

function StrategySymbols({ strategy, color, symbols, onRefresh }) {
  const [symIn, setSymIn]     = useState("");
  const [exchIn, setExchIn]   = useState("NSE");
  const [delTarget, setDelTarget] = useState("");
  const [addMsg, setAddMsg]   = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [delLoading, setDelLoading] = useState(false);

  const handleAdd = async () => {
    if (!symIn.trim()) { setAddMsg("Enter a symbol."); return; }
    setAddLoading(true); setAddMsg("");
    try {
      const res = await api.post(`/api/symbols/${strategy}`, { symbol: symIn.trim().toUpperCase(), exchange: exchIn.trim().toUpperCase() });
      if (res.data.success) { setAddMsg(`✅ Added ${symIn.toUpperCase()}`); setSymIn(""); onRefresh(strategy); }
      else setAddMsg("❌ " + (res.data.error || "Error"));
    } catch (e) { setAddMsg("❌ " + (e.response?.data?.detail || e.message)); }
    finally { setAddLoading(false); }
  };

  const handleDelete = async () => {
    if (!delTarget) return;
    setDelLoading(true);
    try { await api.delete(`/api/symbols/${strategy}/${delTarget}`); setDelTarget(""); onRefresh(strategy); }
    catch (e) { alert("Delete failed: " + (e.response?.data?.detail || e.message)); }
    finally { setDelLoading(false); }
  };

  return (
    <div className="strategy-section">
      <div className="strategy-section-header" style={{ color }}>● {strategy} Symbols</div>
      <div className="table-wrapper" style={{ marginBottom: "14px" }}>
        <table>
          <thead><tr><th>Executed</th><th>Symbol</th><th>Exchange</th><th>Token</th></tr></thead>
          <tbody>
            {!symbols || symbols.length === 0
              ? <tr><td colSpan={4} style={{ color: "#8b949e", textAlign: "center", padding: "20px" }}>No symbols yet.</td></tr>
              : symbols.map(row => (
                <tr key={row.symbol}>
                  <td><span className="pill" style={row.isExecuted ? { background: "#2ea04322", color: "#2ea043", border: "1px solid #2ea043" } : { background: "#30363d", color: "#8b949e", border: "1px solid #30363d" }}>{row.isExecuted ? "Yes" : "No"}</span></td>
                  <td style={{ fontWeight: 600 }}>{row.symbol}</td>
                  <td>{row.exchange}</td>
                  <td style={{ color: "#8b949e" }}>{row.instrument_token}</td>
                </tr>
              ))
            }
          </tbody>
        </table>
      </div>
      <div style={{ display: "flex", gap: "8px", alignItems: "flex-end", flexWrap: "wrap", marginBottom: "10px" }}>
        <div><div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Symbol</div><input type="text" placeholder="e.g. RELIANCE" value={symIn} onChange={e => setSymIn(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAdd()} style={{ width: "160px" }} /></div>
        <div><div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Exchange</div><input type="text" value={exchIn} onChange={e => setExchIn(e.target.value)} style={{ width: "80px" }} /></div>
        <button className="btn-primary" onClick={handleAdd} disabled={addLoading}>{addLoading ? "Adding..." : "➕ Add"}</button>
      </div>
      {addMsg && <div style={{ fontSize: "12px", marginBottom: "10px", color: addMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>{addMsg}</div>}
      <div style={{ display: "flex", gap: "8px", alignItems: "flex-end", flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Delete Symbol</div>
          <select value={delTarget} onChange={e => setDelTarget(e.target.value)} style={{ width: "200px" }}>
            <option value="">— select —</option>
            {(symbols || []).map(s => <option key={s.symbol} value={s.symbol}>{s.symbol}</option>)}
          </select>
        </div>
        <button className="btn-danger" onClick={handleDelete} disabled={!delTarget || delLoading}>{delLoading ? "Deleting..." : "🗑️ Delete"}</button>
      </div>
    </div>
  );
}

export default function SymbolsTab({ symbolsCache, status, onRefreshSymbols }) {
  return (
    <div>
      {status && Object.entries(status).map(([s, info]) => (
        <StrategySymbols key={s} strategy={s} color={info.color} symbols={symbolsCache[s] || []} onRefresh={onRefreshSymbols} />
      ))}
    </div>
  );
}

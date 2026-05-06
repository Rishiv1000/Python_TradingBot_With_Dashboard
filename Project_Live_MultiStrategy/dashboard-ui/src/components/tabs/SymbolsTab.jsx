import { useState } from "react";
import api from "../../api";

// symbols and onRefreshSymbols come from App — no internal fetching
function StrategySymbols({ strategy, color, symbols, onRefreshSymbols }) {
  const [symbolInput, setSymbolInput]   = useState("");
  const [exchangeInput, setExchangeInput] = useState("NSE");
  const [deleteTarget, setDeleteTarget] = useState("");
  const [addMsg, setAddMsg]             = useState("");
  const [addLoading, setAddLoading]     = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const handleAdd = async () => {
    if (!symbolInput.trim()) { setAddMsg("Enter a symbol first."); return; }
    setAddLoading(true);
    setAddMsg("");
    try {
      const res = await api.post(`/api/symbols/${strategy}`, {
        symbol:   symbolInput.trim().toUpperCase(),
        exchange: exchangeInput.trim().toUpperCase(),
      });
      if (res.data.success) {
        setAddMsg(`✅ Added ${symbolInput.toUpperCase()} (token: ${res.data.token})`);
        setSymbolInput("");
        onRefreshSymbols(strategy);   // refresh only this strategy's symbols
      } else {
        setAddMsg("❌ " + (res.data.error || "Unknown error"));
      }
    } catch (e) {
      setAddMsg("❌ " + (e.response?.data?.detail || e.message));
    } finally {
      setAddLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/api/symbols/${strategy}/${deleteTarget}`);
      setDeleteTarget("");
      onRefreshSymbols(strategy);
    } catch (e) {
      alert("Delete failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div className="strategy-section">
      <div className="strategy-section-header" style={{ color }}>
        ● {strategy} Symbols
      </div>

      <div className="table-wrapper" style={{ marginBottom: "14px" }}>
        <table>
          <thead>
            <tr>
              <th>Executed</th>
              <th>Symbol</th>
              <th>Exchange</th>
              <th>Instrument Token</th>
            </tr>
          </thead>
          <tbody>
            {!symbols || symbols.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ color: "#8b949e", textAlign: "center", padding: "20px" }}>
                  No symbols added yet.
                </td>
              </tr>
            ) : (
              symbols.map((row) => (
                <tr key={row.symbol}>
                  <td>
                    <span className="pill" style={
                      row.isExecuted
                        ? { background: "#2ea04322", color: "#2ea043", border: "1px solid #2ea043" }
                        : { background: "#30363d",   color: "#8b949e", border: "1px solid #30363d" }
                    }>
                      {row.isExecuted ? "Yes" : "No"}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{row.symbol}</td>
                  <td>{row.exchange}</td>
                  <td style={{ color: "#8b949e" }}>{row.instrument_token}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Add */}
      <div style={{ display: "flex", gap: "8px", alignItems: "flex-end", flexWrap: "wrap", marginBottom: "10px" }}>
        <div>
          <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Symbol</div>
          <input
            type="text"
            placeholder="e.g. RELIANCE"
            value={symbolInput}
            onChange={(e) => setSymbolInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            style={{ width: "160px" }}
          />
        </div>
        <div>
          <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Exchange</div>
          <input
            type="text"
            value={exchangeInput}
            onChange={(e) => setExchangeInput(e.target.value)}
            style={{ width: "80px" }}
          />
        </div>
        <button className="btn-primary" onClick={handleAdd} disabled={addLoading}>
          {addLoading ? "Adding..." : "➕ Add"}
        </button>
      </div>
      {addMsg && (
        <div style={{ fontSize: "12px", marginBottom: "10px", color: addMsg.startsWith("✅") ? "#2ea043" : "#da3633" }}>
          {addMsg}
        </div>
      )}

      {/* Delete */}
      <div style={{ display: "flex", gap: "8px", alignItems: "flex-end", flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Delete Symbol</div>
          <select value={deleteTarget} onChange={(e) => setDeleteTarget(e.target.value)} style={{ width: "200px" }}>
            <option value="">— select symbol —</option>
            {(symbols || []).map((s) => (
              <option key={s.symbol} value={s.symbol}>{s.symbol}</option>
            ))}
          </select>
        </div>
        <button className="btn-danger" onClick={handleDelete} disabled={!deleteTarget || deleteLoading}>
          {deleteLoading ? "Deleting..." : "🗑️ Delete"}
        </button>
      </div>
    </div>
  );
}

export default function SymbolsTab({ symbolsCache, status, onRefreshSymbols }) {
  const strategies = status ? Object.entries(status) : [];
  return (
    <div>
      {strategies.map(([strategy, info]) => (
        <StrategySymbols
          key={strategy}
          strategy={strategy}
          color={info.color}
          symbols={symbolsCache[strategy] || []}
          onRefreshSymbols={onRefreshSymbols}
        />
      ))}
    </div>
  );
}

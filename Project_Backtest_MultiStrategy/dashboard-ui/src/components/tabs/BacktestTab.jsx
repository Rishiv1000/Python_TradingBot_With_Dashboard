import { useState, useEffect } from "react";
import api from "../../api";

export default function BacktestTab({ status }) {
  const strategies   = status ? Object.keys(status) : ["GREEN", "RSI"];
  const [strategy, setStrategy]   = useState(strategies[0] || "GREEN");
  const [days, setDays]           = useState(30);
  const [running, setRunning]     = useState(false);
  const [runResult, setRunResult] = useState(null);
  const [results, setResults]     = useState([]);
  const [selected, setSelected]   = useState(null);
  const [resultData, setResultData] = useState(null);
  const [loadingResult, setLoadingResult] = useState(false);

  const fetchResults = () => {
    api.get("/api/backtest/results").then(r => setResults(r.data)).catch(() => {});
  };

  useEffect(() => { fetchResults(); }, []);

  const handleRun = async () => {
    setRunning(true); setRunResult(null);
    try {
      const res = await api.post("/api/backtest/run", { strategy, days });
      setRunResult(res.data);
      fetchResults();
    } catch (e) {
      setRunResult({ success: false, error: e.response?.data?.detail || e.message });
    } finally { setRunning(false); }
  };

  const handleSelectResult = async (filename) => {
    setSelected(filename); setLoadingResult(true); setResultData(null);
    try {
      const res = await api.get(`/api/backtest/result/${filename}`);
      setResultData(res.data);
    } catch { setResultData(null); }
    finally { setLoadingResult(false); }
  };

  return (
    <div>
      <div className="section-title">🔬 Run Backtest</div>
      <div style={{ display: "flex", gap: "16px", alignItems: "flex-end", flexWrap: "wrap", marginBottom: "16px" }}>
        <div>
          <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Strategy</div>
          <select value={strategy} onChange={e => setStrategy(e.target.value)} style={{ width: "160px" }}>
            {strategies.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Days: <strong style={{ color: "#f0f6fc" }}>{days}</strong></div>
          <input type="range" min={1} max={365} value={days} onChange={e => setDays(Number(e.target.value))} style={{ width: "200px", padding: 0, border: "none", background: "transparent", cursor: "pointer" }} />
        </div>
        <button className="btn-purple" onClick={handleRun} disabled={running} style={{ minWidth: "120px" }}>
          {running ? "⏳ Running..." : "▶ Run Backtest"}
        </button>
      </div>

      {runResult && (
        <div style={{ background: runResult.success ? "#2ea04322" : "#da363322", border: `1px solid ${runResult.success ? "#2ea043" : "#da3633"}`, borderRadius: "8px", padding: "12px 16px", marginBottom: "20px" }}>
          {runResult.success
            ? <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
                <span style={{ color: "#2ea043", fontWeight: 700 }}>✅ Backtest Complete</span>
                <span>Trades: <strong>{runResult.trades}</strong></span>
                <span>PnL: <strong style={{ color: runResult.total_pnl >= 0 ? "#2ea043" : "#da3633" }}>₹ {runResult.total_pnl}</strong></span>
                <span>Win Rate: <strong>{runResult.win_rate}%</strong></span>
              </div>
            : <span style={{ color: "#da3633" }}>❌ {runResult.error}</span>
          }
        </div>
      )}

      <hr className="divider" />
      <div className="section-title">📁 Backtest Results</div>

      {results.length === 0
        ? <div style={{ color: "#8b949e" }}>No results yet. Run a backtest first.</div>
        : <>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "16px" }}>
            {results.map(r => (
              <button key={r.filename} className={selected === r.filename ? "btn-blue btn-sm" : "btn-secondary btn-sm"} onClick={() => handleSelectResult(r.filename)}>
                {r.filename.replace(".xlsx", "")}
              </button>
            ))}
          </div>

          {loadingResult && <div style={{ color: "#8b949e" }}>Loading...</div>}

          {resultData && (
            <>
              <div style={{ display: "flex", gap: "12px", marginBottom: "16px", flexWrap: "wrap" }}>
                <div className="metric-box"><div className="metric-label">Trades</div><div className="metric-value">{resultData.trades}</div></div>
                <div className="metric-box"><div className="metric-label">Total PnL</div><div className="metric-value" style={{ color: resultData.total_pnl >= 0 ? "#2ea043" : "#da3633" }}>₹ {resultData.total_pnl}</div></div>
                <div className="metric-box"><div className="metric-label">Win Rate</div><div className="metric-value">{resultData.win_rate}%</div></div>
              </div>
              <div className="table-wrapper">
                <table>
                  <thead><tr>{resultData.columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
                  <tbody>
                    {resultData.data.map((row, i) => (
                      <tr key={i}>
                        {resultData.columns.map(c => (
                          <td key={c} style={{ whiteSpace: "nowrap", color: c === "pnl" ? (Number(row[c]) >= 0 ? "#2ea043" : "#da3633") : undefined, fontWeight: c === "pnl" ? 700 : undefined }}>
                            {c === "pnl" && row[c] != null ? `₹ ${Number(row[c]).toFixed(2)}` : row[c] != null ? String(row[c]) : "—"}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      }
    </div>
  );
}

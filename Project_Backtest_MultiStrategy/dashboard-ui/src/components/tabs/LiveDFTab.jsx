import { useState, useEffect, useCallback } from "react";
import api from "../../api";

function useNextCandleCountdown() {
  const [countdown, setCountdown] = useState(0);
  useEffect(() => {
    const tick = () => setCountdown(60 - new Date().getSeconds());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return countdown;
}

function StrategyLiveDF({ strategy, color, symbols }) {
  const symNames = (symbols || []).map(s => s.symbol);
  const [selected, setSelected] = useState(symNames[0] || "");
  const [dfData, setDfData]     = useState(null);
  const [loading, setLoading]   = useState(false);
  const [rows, setRows]         = useState(5);
  const countdown = useNextCandleCountdown();

  useEffect(() => {
    if (symNames.length > 0 && !symNames.includes(selected)) setSelected(symNames[0]);
  }, [symNames.join(",")]);

  const fetchDF = useCallback(() => {
    if (!selected) return;
    setLoading(true);
    api.get(`/api/df/${strategy}/${selected}`)
      .then(res => setDfData(res.data))
      .catch(() => setDfData(null))
      .finally(() => setLoading(false));
  }, [strategy, selected]);

  useEffect(() => { fetchDF(); }, [fetchDF]);

  return (
    <div className="strategy-section">
      <div className="strategy-section-header" style={{ color }}>● {strategy} — Live DataFrame Cache</div>

      {symNames.length === 0 ? (
        <div style={{ color: "#8b949e" }}>No symbols configured.</div>
      ) : (
        <>
          {/* Controls row */}
          <div style={{ display: "flex", gap: "12px", alignItems: "flex-end", flexWrap: "wrap", marginBottom: "14px" }}>
            <div>
              <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Symbol</div>
              <select value={selected} onChange={e => setSelected(e.target.value)} style={{ width: "200px" }}>
                {symNames.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            {/* Reload button right next to symbol */}
            <button
              className="btn-secondary btn-sm"
              onClick={fetchDF}
              disabled={loading}
              style={{ alignSelf: "flex-end" }}
            >
              {loading ? "⏳" : "🔄 Reload"}
            </button>
            <div>
              <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Rows: <strong style={{ color: "#f0f6fc" }}>{rows}</strong></div>
              <input type="range" min={5} max={500} step={5} value={rows} onChange={e => setRows(Number(e.target.value))} style={{ width: "120px" }} />
            </div>
          </div>

          {loading ? (
            <div style={{ color: "#8b949e" }}>Loading...</div>
          ) : dfData ? (
            <>
              <div style={{ display: "flex", gap: "12px", marginBottom: "16px", flexWrap: "wrap" }}>
                <div className="metric-box">
                  <div className="metric-label">Total Candles</div>
                  <div className="metric-value">{dfData.candle_count}</div>
                </div>
                <div className="metric-box">
                  <div className="metric-label">Last Candle</div>
                  <div className="metric-value" style={{ fontSize: "14px", paddingTop: "4px" }}>{dfData.last_candle || "—"}</div>
                </div>
                <div className="metric-box">
                  <div className="metric-label">Showing</div>
                  <div className="metric-value">{Math.min(rows, dfData.data?.length || 0)}</div>
                </div>
                {/* Next candle countdown */}
                <div className="metric-box" style={{ borderColor: countdown <= 5 ? "#e3b341" : "#30363d" }}>
                  <div className="metric-label" style={{ color: countdown <= 5 ? "#e3b341" : "#8b949e" }}>Next Candle</div>
                  <div className="metric-value" style={{ color: countdown <= 5 ? "#e3b341" : "#f0f6fc", fontVariantNumeric: "tabular-nums" }}>
                    {countdown}s
                  </div>
                </div>
              </div>

              {dfData.data?.length > 0 ? (
                <div className="table-wrapper">
                  <table>
                    <thead><tr>{dfData.columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
                    <tbody>
                      {dfData.data.slice(-rows).map((row, i) => (
                        <tr key={i}>{dfData.columns.map(c => (
                          <td key={c} style={{ whiteSpace: "nowrap" }}>
                            {row[c] != null ? String(row[c]) : "—"}
                          </td>
                        ))}</tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ color: "#8b949e" }}>No cache data yet. Start the strategy first.</div>
              )}
            </>
          ) : (
            <div style={{ color: "#8b949e" }}>No cache data available.</div>
          )}
        </>
      )}
    </div>
  );
}

export default function LiveDFTab({ symbolsCache, status }) {
  return (
    <div>
      {status && Object.entries(status).map(([s, info]) => (
        <StrategyLiveDF key={s} strategy={s} color={info.color} symbols={symbolsCache[s] || []} />
      ))}
    </div>
  );
}

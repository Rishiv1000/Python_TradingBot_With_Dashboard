import { useState, useEffect, useCallback } from "react";
import api from "../../api";

// Countdown to next 1-minute candle boundary
function useNextCandleCountdown() {
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const secondsLeft = 60 - now.getSeconds();
      setCountdown(secondsLeft);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return countdown;
}

function StrategyLiveDF({ strategy, color, symbols }) {
  const symNames = (symbols || []).map((s) => s.symbol);
  const [selectedSymbol, setSelectedSymbol] = useState(symNames[0] || "");
  const [dfData, setDfData]     = useState(null);
  const [loading, setLoading]   = useState(false);
  const [rowsToShow, setRowsToShow] = useState(5);
  const countdown = useNextCandleCountdown();

  useEffect(() => {
    if (symNames.length > 0 && !symNames.includes(selectedSymbol)) {
      setSelectedSymbol(symNames[0]);
    }
  }, [symNames.join(",")]);

  const fetchDF = useCallback(() => {
    if (!selectedSymbol) return;
    setLoading(true);
    api.get(`/api/df/${strategy}/${selectedSymbol}`)
      .then((res) => setDfData(res.data))
      .catch(() => setDfData(null))
      .finally(() => setLoading(false));
  }, [strategy, selectedSymbol]);

  useEffect(() => {
    fetchDF();
  }, [fetchDF]);

  return (
    <div className="strategy-section">
      <div className="strategy-section-header" style={{ color }}>
        ● {strategy} — Live DataFrame Cache
      </div>

      {symNames.length === 0 ? (
        <div style={{ color: "#8b949e", padding: "12px 0" }}>No symbols configured.</div>
      ) : (
        <>
          {/* Controls row */}
          <div style={{ display: "flex", gap: "16px", alignItems: "flex-end", flexWrap: "wrap", marginBottom: "14px" }}>
            <div>
              <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>Symbol</div>
              <select
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
                style={{ width: "200px" }}
              >
                {symNames.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <div style={{ fontSize: "11px", color: "#8b949e", marginBottom: "4px" }}>
                Rows: <strong style={{ color: "#f0f6fc" }}>{rowsToShow}</strong>
              </div>
              <input
                type="range"
                min={5}
                max={500}
                step={5}
                value={rowsToShow}
                onChange={(e) => setRowsToShow(Number(e.target.value))}
                style={{ width: "160px", padding: 0, border: "none", background: "transparent", cursor: "pointer" }}
              />
            </div>
            {/* Reload button */}
            <button
              className="btn-secondary btn-sm"
              onClick={fetchDF}
              disabled={loading}
              style={{ alignSelf: "flex-end" }}
            >
              {loading ? "⏳" : "🔄 Reload DF"}
            </button>
          </div>

          {loading ? (
            <div style={{ color: "#8b949e" }}>Loading...</div>
          ) : dfData ? (
            <>
              {/* Metrics row */}
              <div style={{ display: "flex", gap: "12px", marginBottom: "16px", flexWrap: "wrap" }}>
                <div className="metric-box">
                  <div className="metric-label">Total Candles</div>
                  <div className="metric-value">{dfData.candle_count}</div>
                </div>
                <div className="metric-box">
                  <div className="metric-label">Last Candle</div>
                  <div className="metric-value" style={{ fontSize: "14px", paddingTop: "4px" }}>
                    {dfData.last_candle || "—"}
                  </div>
                </div>
                <div className="metric-box">
                  <div className="metric-label">Showing</div>
                  <div className="metric-value">{Math.min(rowsToShow, dfData.data?.length || 0)}</div>
                </div>
                {/* Next candle countdown */}
                <div className="metric-box" style={{ borderColor: countdown <= 5 ? "#e3b341" : "#30363d" }}>
                  <div className="metric-label" style={{ color: countdown <= 5 ? "#e3b341" : "#8b949e" }}>
                    Next Candle In
                  </div>
                  <div className="metric-value" style={{ color: countdown <= 5 ? "#e3b341" : "#f0f6fc", fontVariantNumeric: "tabular-nums" }}>
                    {countdown}s
                  </div>
                </div>
              </div>

              {dfData.data && dfData.data.length > 0 ? (
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>{dfData.columns.map((col) => <th key={col}>{col}</th>)}</tr>
                    </thead>
                    <tbody>
                      {dfData.data.slice(-rowsToShow).map((row, i) => (
                        <tr key={i}>
                          {dfData.columns.map((col) => (
                            <td key={col} style={{ whiteSpace: "nowrap" }}>
                              {row[col] !== undefined && row[col] !== null ? String(row[col]) : "—"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ color: "#8b949e" }}>No cache data yet. Start the strategy to populate data.</div>
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
  const strategies = status ? Object.entries(status) : [];
  return (
    <div>
      {strategies.map(([strategy, info]) => (
        <StrategyLiveDF
          key={strategy}
          strategy={strategy}
          color={info.color}
          symbols={symbolsCache[strategy] || []}
        />
      ))}
    </div>
  );
}

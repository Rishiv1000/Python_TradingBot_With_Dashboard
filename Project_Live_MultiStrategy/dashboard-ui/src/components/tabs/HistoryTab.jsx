import { useState, useEffect } from "react";
import api from "../../api";

export default function HistoryTab() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    try {
      const res = await api.get("/api/history");
      setHistory(res.data);
    } catch {
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 5000);
    return () => clearInterval(interval);
  }, []);

  const totalPnl = history.reduce((sum, t) => sum + (t.pnl || 0), 0);
  const wins = history.filter((t) => (t.pnl || 0) > 0).length;
  const winRate = history.length > 0 ? (wins / history.length) * 100 : 0;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
        <div className="section-title">📜 Trade History</div>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <div className="metric-box" style={{ minWidth: "auto", padding: "8px 16px" }}>
            <div style={{ fontSize: "10px", color: "#8b949e", marginBottom: "2px" }}>TOTAL TRADES</div>
            <div style={{ fontWeight: 700, fontSize: "16px" }}>{history.length}</div>
          </div>
          <div className="metric-box" style={{ minWidth: "auto", padding: "8px 16px" }}>
            <div style={{ fontSize: "10px", color: "#8b949e", marginBottom: "2px" }}>TOTAL PNL</div>
            <div
              style={{
                fontWeight: 700,
                fontSize: "16px",
                color: totalPnl >= 0 ? "#2ea043" : "#da3633",
              }}
            >
              ₹ {totalPnl.toFixed(2)}
            </div>
          </div>
          <div className="metric-box" style={{ minWidth: "auto", padding: "8px 16px" }}>
            <div style={{ fontSize: "10px", color: "#8b949e", marginBottom: "2px" }}>WIN RATE</div>
            <div style={{ fontWeight: 700, fontSize: "16px" }}>{winRate.toFixed(1)}%</div>
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ color: "#8b949e" }}>Loading...</div>
      ) : history.length === 0 ? (
        <div style={{ color: "#8b949e", padding: "20px 0" }}>No trade history yet.</div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Symbol</th>
                <th>Buy Time</th>
                <th>Buy Price</th>
                <th>Sell Time</th>
                <th>Sell Price</th>
                <th>PnL</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {history.map((trade, i) => (
                <tr key={i}>
                  <td>
                    <span
                      className="pill"
                      style={{
                        background: trade.strategy === "GREEN" ? "#2ea04322" : "#ff7b7222",
                        color: trade.strategy === "GREEN" ? "#2ea043" : "#ff7b72",
                        border: `1px solid ${trade.strategy === "GREEN" ? "#2ea043" : "#ff7b72"}`,
                      }}
                    >
                      {trade.strategy}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{trade.symbol}</td>
                  <td style={{ color: "#8b949e", whiteSpace: "nowrap", fontSize: "12px" }}>
                    {trade.buytime || "—"}
                  </td>
                  <td style={{ color: "#58a6ff" }}>
                    {trade.buyprice != null ? `₹ ${Number(trade.buyprice).toFixed(2)}` : "—"}
                  </td>
                  <td style={{ color: "#8b949e", whiteSpace: "nowrap", fontSize: "12px" }}>
                    {trade.selltime || "—"}
                  </td>
                  <td style={{ color: "#58a6ff" }}>
                    {trade.sellprice != null ? `₹ ${Number(trade.sellprice).toFixed(2)}` : "—"}
                  </td>
                  <td
                    style={{
                      fontWeight: 700,
                      color: (trade.pnl || 0) >= 0 ? "#2ea043" : "#da3633",
                    }}
                  >
                    {trade.pnl != null ? `₹ ${Number(trade.pnl).toFixed(2)}` : "—"}
                  </td>
                  <td style={{ color: "#8b949e", fontSize: "12px" }}>{trade.reason || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

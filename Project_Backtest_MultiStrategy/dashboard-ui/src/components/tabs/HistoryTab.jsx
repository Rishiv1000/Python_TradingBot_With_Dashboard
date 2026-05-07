import { useState, useEffect } from "react";
import api from "../../api";

export default function HistoryTab() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = () => {
    api.get("/api/history")
      .then(r => setHistory(r.data))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchHistory();
    const id = setInterval(fetchHistory, 5000);
    return () => clearInterval(id);
  }, []);

  const totalPnl = history.reduce((s, t) => s + (t.pnl || 0), 0);
  const wins     = history.filter(t => (t.pnl || 0) > 0).length;
  const winRate  = history.length > 0 ? (wins / history.length) * 100 : 0;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
        <div className="section-title">📜 Trade History</div>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <div className="metric-box" style={{ minWidth: "auto", padding: "8px 16px" }}><div style={{ fontSize: "10px", color: "#8b949e", marginBottom: "2px" }}>TRADES</div><div style={{ fontWeight: 700, fontSize: "16px" }}>{history.length}</div></div>
          <div className="metric-box" style={{ minWidth: "auto", padding: "8px 16px" }}><div style={{ fontSize: "10px", color: "#8b949e", marginBottom: "2px" }}>TOTAL PNL</div><div style={{ fontWeight: 700, fontSize: "16px", color: totalPnl >= 0 ? "#2ea043" : "#da3633" }}>₹ {totalPnl.toFixed(2)}</div></div>
          <div className="metric-box" style={{ minWidth: "auto", padding: "8px 16px" }}><div style={{ fontSize: "10px", color: "#8b949e", marginBottom: "2px" }}>WIN RATE</div><div style={{ fontWeight: 700, fontSize: "16px" }}>{winRate.toFixed(1)}%</div></div>
        </div>
      </div>
      {loading ? <div style={{ color: "#8b949e" }}>Loading...</div>
      : history.length === 0 ? <div style={{ color: "#8b949e" }}>No trade history yet.</div>
      : <div className="table-wrapper">
          <table>
            <thead><tr><th>Strategy</th><th>Symbol</th><th>Buy Time</th><th>Buy Price</th><th>Sell Time</th><th>Sell Price</th><th>PnL</th><th>Reason</th><th>Mode</th></tr></thead>
            <tbody>
              {history.map((t, i) => (
                <tr key={i}>
                  <td><span className="pill" style={{ background: t.strategy === "GREEN" ? "#2ea04322" : "#58a6ff22", color: t.strategy === "GREEN" ? "#2ea043" : "#58a6ff", border: `1px solid ${t.strategy === "GREEN" ? "#2ea043" : "#58a6ff"}` }}>{t.strategy}</span></td>
                  <td style={{ fontWeight: 600 }}>{t.symbol}</td>
                  <td style={{ color: "#8b949e", fontSize: "12px" }}>{t.buytime || "—"}</td>
                  <td style={{ color: "#58a6ff" }}>{t.buyprice != null ? `₹ ${Number(t.buyprice).toFixed(2)}` : "—"}</td>
                  <td style={{ color: "#8b949e", fontSize: "12px" }}>{t.selltime || "—"}</td>
                  <td style={{ color: "#58a6ff" }}>{t.sellprice != null ? `₹ ${Number(t.sellprice).toFixed(2)}` : "—"}</td>
                  <td style={{ fontWeight: 700, color: (t.pnl || 0) >= 0 ? "#2ea043" : "#da3633" }}>{t.pnl != null ? `₹ ${Number(t.pnl).toFixed(2)}` : "—"}</td>
                  <td style={{ color: "#8b949e", fontSize: "12px" }}>{t.reason || "—"}</td>
                  <td><span className="pill" style={{ background: "#58a6ff22", color: "#58a6ff", border: "1px solid #58a6ff" }}>{t.mode || "PAPER"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      }
    </div>
  );
}

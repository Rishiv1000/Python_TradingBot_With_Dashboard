import { useState, useEffect } from "react";
import api from "../../api";

export default function PositionsTab() {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading]     = useState(true);

  const fetchPositions = () => {
    api.get("/api/positions")
      .then(r => setPositions(r.data))
      .catch(() => setPositions([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPositions();
    const id = setInterval(fetchPositions, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
        <div className="section-title">📂 Open Positions</div>
        <div className="metric-box" style={{ minWidth: "auto", padding: "8px 16px" }}>
          <span style={{ fontSize: "12px", color: "#8b949e" }}>Total: </span>
          <span style={{ fontWeight: 700, fontSize: "16px" }}>{positions.length}</span>
        </div>
      </div>
      {loading ? <div style={{ color: "#8b949e" }}>Loading...</div>
      : positions.length === 0 ? <div style={{ color: "#8b949e" }}>No open positions.</div>
      : <div className="table-wrapper">
          <table>
            <thead><tr><th>Strategy</th><th>Symbol</th><th>Buy Price</th><th>Buy Time</th><th>Product</th><th>Mode</th></tr></thead>
            <tbody>
              {positions.map((p, i) => (
                <tr key={i}>
                  <td><span className="pill" style={{ background: p.strategy === "GREEN" ? "#2ea04322" : "#58a6ff22", color: p.strategy === "GREEN" ? "#2ea043" : "#58a6ff", border: `1px solid ${p.strategy === "GREEN" ? "#2ea043" : "#58a6ff"}` }}>{p.strategy}</span></td>
                  <td style={{ fontWeight: 600 }}>{p.symbol}</td>
                  <td style={{ color: "#58a6ff" }}>{p.buyprice != null ? `₹ ${Number(p.buyprice).toFixed(2)}` : "—"}</td>
                  <td style={{ color: "#8b949e", fontSize: "12px" }}>{p.buytime || "—"}</td>
                  <td>{p.product || "—"}</td>
                  <td><span className="pill" style={{ background: "#58a6ff22", color: "#58a6ff", border: "1px solid #58a6ff" }}>{p.mode || "PAPER"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      }
    </div>
  );
}

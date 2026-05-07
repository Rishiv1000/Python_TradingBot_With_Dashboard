import { useState, useEffect } from "react";
import api from "../../api";

export default function PositionsTab() {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchPositions = async () => {
    try {
      const res = await api.get("/api/positions");
      setPositions(res.data);
    } catch {
      setPositions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
        <div className="section-title">📂 Open Positions</div>
        <div className="metric-box" style={{ minWidth: "auto", padding: "8px 16px" }}>
          <span style={{ fontSize: "12px", color: "#8b949e" }}>Total Open: </span>
          <span style={{ fontWeight: 700, fontSize: "16px" }}>{positions.length}</span>
        </div>
      </div>

      {loading ? (
        <div style={{ color: "#8b949e" }}>Loading...</div>
      ) : positions.length === 0 ? (
        <div style={{ color: "#8b949e", padding: "20px 0" }}>No open positions.</div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Symbol</th>
                <th>Buy Price</th>
                <th>Buy Time</th>
                <th>Product</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos, i) => (
                <tr key={i}>
                  <td>
                    <span
                      className="pill"
                      style={{
                        background: pos.strategy === "GREEN" ? "#2ea04322" : "#ff7b7222",
                        color: pos.strategy === "GREEN" ? "#2ea043" : "#ff7b72",
                        border: `1px solid ${pos.strategy === "GREEN" ? "#2ea043" : "#ff7b72"}`,
                      }}
                    >
                      {pos.strategy}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{pos.symbol}</td>
                  <td style={{ color: "#58a6ff" }}>
                    {pos.buyprice != null ? `₹ ${Number(pos.buyprice).toFixed(2)}` : "—"}
                  </td>
                  <td style={{ color: "#8b949e", whiteSpace: "nowrap" }}>{pos.buytime || "—"}</td>
                  <td>{pos.product || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function StrategyCards({ status }) {
  if (!status) return null;
  return (
    <div style={{ display: "flex", gap: "16px", marginBottom: "24px", flexWrap: "wrap" }}>
      {Object.entries(status).map(([strategy, info]) => {
        const color = info.running ? "#2ea043" : "#da3633";
        return (
          <div key={strategy} className="card" style={{ flex: "1 1 200px", borderLeft: `4px solid ${info.color}`, minWidth: "180px" }}>
            <div style={{ fontSize: "18px", fontWeight: 900, color: info.color, marginBottom: "6px" }}>{strategy}</div>
            <span className="pill" style={{ background: color + "22", color, border: `1px solid ${color}`, marginBottom: "10px", display: "inline-block" }}>
              {info.running ? "RUNNING" : "STOPPED"}
            </span>
            <div style={{ display: "flex", gap: "16px", marginTop: "8px" }}>
              <div><div style={{ fontSize: "11px", color: "#8b949e", fontWeight: 600 }}>SYMBOLS</div><div style={{ fontSize: "20px", fontWeight: 700 }}>{info.symbol_count}</div></div>
              <div><div style={{ fontSize: "11px", color: "#8b949e", fontWeight: 600 }}>OPEN</div><div style={{ fontSize: "20px", fontWeight: 700 }}>{info.open_count}</div></div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

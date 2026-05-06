export default function StrategyCards({ status }) {
  if (!status) return null;

  // trading_enabled is same for all strategies (global flag)
  const tradingEnabled = Object.values(status).some(s => s.trading_enabled);

  return (
    <div>
      {/* Trading lock banner */}
      {!tradingEnabled && (
        <div style={{
          background: "#da363322",
          border: "1px solid #da3633",
          borderRadius: "8px",
          padding: "10px 16px",
          marginBottom: "16px",
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}>
          <span style={{ fontSize: "18px" }}>🔒</span>
          <div>
            <div style={{ fontWeight: 700, color: "#da3633", fontSize: "14px" }}>
              Real Trading Blocked By Backend
            </div>
            <div style={{ color: "#8b949e", fontSize: "12px", marginTop: "2px" }}>
              Set <code style={{ background: "#161b22", padding: "1px 6px", borderRadius: "4px" }}>REAL_TRADING_ENABLED = True</code> in <code style={{ background: "#161b22", padding: "1px 6px", borderRadius: "4px" }}>shared/base_config.py</code> to unlock strategies.
            </div>
          </div>
        </div>
      )}

      {/* Strategy cards */}
      <div style={{ display: "flex", gap: "16px", marginBottom: "24px", flexWrap: "wrap" }}>
        {Object.entries(status).map(([strategy, info]) => {
          const running     = info.running;
          const statusColor = running ? "#2ea043" : "#da3633";
          const statusLabel = running ? "RUNNING" : "STOPPED";
          return (
            <div
              key={strategy}
              className="card"
              style={{
                flex: "1 1 200px",
                borderLeft: `4px solid ${info.color}`,
                minWidth: "180px",
                opacity: !tradingEnabled ? 0.6 : 1,
              }}
            >
              <div style={{ fontSize: "18px", fontWeight: 900, color: info.color, marginBottom: "6px" }}>
                {strategy}
                {!tradingEnabled && (
                  <span style={{ fontSize: "13px", marginLeft: "8px", color: "#da3633" }}>🔒</span>
                )}
              </div>
              <span
                className="pill"
                style={{
                  background: statusColor + "22",
                  color: statusColor,
                  border: `1px solid ${statusColor}`,
                  marginBottom: "10px",
                  display: "inline-block",
                }}
              >
                {statusLabel}
              </span>
              <div style={{ display: "flex", gap: "16px", marginTop: "8px" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "#8b949e", fontWeight: 600 }}>SYMBOLS</div>
                  <div style={{ fontSize: "20px", fontWeight: 700 }}>{info.symbol_count}</div>
                </div>
                <div>
                  <div style={{ fontSize: "11px", color: "#8b949e", fontWeight: 600 }}>OPEN</div>
                  <div style={{ fontSize: "20px", fontWeight: 700 }}>{info.open_count}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

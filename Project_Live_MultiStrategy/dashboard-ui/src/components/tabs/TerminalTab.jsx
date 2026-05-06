import { useState, useEffect, useRef } from "react";
import api from "../../api";

function StrategyTerminal({ strategy, color }) {
  const [lines, setLines] = useState("No log yet. Start the strategy first.");
  const [loading, setLoading] = useState(false);
  const termRef = useRef(null);

  const fetchLog = async () => {
    try {
      const res = await api.get(`/api/terminal/${strategy}`);
      setLines(res.data.lines || "Log is empty.");
    } catch {
      setLines("Error reading log.");
    }
  };

  useEffect(() => {
    fetchLog();
    const interval = setInterval(fetchLog, 3000);
    return () => clearInterval(interval);
  }, [strategy]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (termRef.current) {
      termRef.current.scrollTop = termRef.current.scrollHeight;
    }
  }, [lines]);

  const handleClear = async () => {
    setLoading(true);
    try {
      await api.delete(`/api/terminal/${strategy}`);
      setLines("Log cleared.");
    } catch {
      alert("Failed to clear log.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="strategy-section">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "10px",
          paddingBottom: "8px",
          borderBottom: "1px solid #30363d",
        }}
      >
        <div className="strategy-section-header" style={{ color, marginBottom: 0, borderBottom: "none" }}>
          ● {strategy} Terminal
        </div>
        <button className="btn-secondary btn-sm" onClick={handleClear} disabled={loading}>
          🗑️ Clear
        </button>
      </div>
      <div className="terminal-block" ref={termRef}>
        {lines}
      </div>
    </div>
  );
}

export default function TerminalTab({ status }) {
  const strategies = status ? Object.entries(status) : [];
  return (
    <div>
      {strategies.map(([strategy, info]) => (
        <StrategyTerminal key={strategy} strategy={strategy} color={info.color} />
      ))}
    </div>
  );
}

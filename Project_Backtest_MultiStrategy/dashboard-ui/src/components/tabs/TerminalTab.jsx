import { useState, useEffect, useRef } from "react";
import api from "../../api";

function StrategyTerminal({ strategy, color }) {
  const [lines, setLines]     = useState("No log yet.");
  const [loading, setLoading] = useState(false);
  const termRef               = useRef(null);

  const fetchLog = () => {
    api.get(`/api/terminal/${strategy}`).then(r => setLines(r.data.lines || "Log is empty.")).catch(() => {});
  };

  useEffect(() => {
    fetchLog();
    const id = setInterval(fetchLog, 3000);
    return () => clearInterval(id);
  }, [strategy]);

  useEffect(() => {
    if (termRef.current) termRef.current.scrollTop = termRef.current.scrollHeight;
  }, [lines]);

  const handleClear = async () => {
    setLoading(true);
    try { await api.delete(`/api/terminal/${strategy}`); setLines("Log cleared."); }
    catch { alert("Failed to clear."); }
    finally { setLoading(false); }
  };

  return (
    <div className="strategy-section">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px", paddingBottom: "8px", borderBottom: "1px solid #30363d" }}>
        <div className="strategy-section-header" style={{ color, marginBottom: 0, borderBottom: "none" }}>● {strategy} Terminal</div>
        <button className="btn-secondary btn-sm" onClick={handleClear} disabled={loading}>🗑️ Clear</button>
      </div>
      <div className="terminal-block" ref={termRef}>{lines}</div>
    </div>
  );
}

export default function TerminalTab({ status }) {
  return (
    <div>
      {status && Object.entries(status).map(([s, info]) => (
        <StrategyTerminal key={s} strategy={s} color={info.color} />
      ))}
    </div>
  );
}

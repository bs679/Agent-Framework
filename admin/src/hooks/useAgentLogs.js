import { useState, useCallback } from "react";

export default function useAgentLogs() {
  const [logs, setLogs] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchLogs = useCallback(async (agentId, tail = 50) => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("admin_token") || "";
      const res = await fetch(
        `/api/v1/admin/agents/${agentId}/logs?tail=${tail}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) {
        setError(`Failed to fetch logs: ${res.status}`);
        setLoading(false);
        return;
      }
      const json = await res.json();
      setLogs(json);
    } catch (err) {
      setError("Unable to fetch logs");
    } finally {
      setLoading(false);
    }
  }, []);

  const clearLogs = useCallback(() => {
    setLogs(null);
    setError(null);
  }, []);

  return { logs, loading, error, fetchLogs, clearLogs };
}

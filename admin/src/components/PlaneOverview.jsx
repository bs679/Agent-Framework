/**
 * PlaneOverview — main view listing all agents in the plane.
 * Polls /api/v1/admin/plane every 30 seconds via usePlaneStatus hook.
 */

import { useState, useCallback } from "react";
import AgentRow from "./AgentRow";
import usePlaneStatus from "../hooks/usePlaneStatus";

function relativeTime(date) {
  if (!date) return "";
  const diff = Date.now() - date.getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 10) return "just now";
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  return `${mins}m ago`;
}

export default function PlaneOverview() {
  const { data, error, loading, lastFetched, refresh } = usePlaneStatus();
  const [expandedId, setExpandedId] = useState(null);

  const handleToggle = useCallback((agentId) => {
    setExpandedId((prev) => (prev === agentId ? null : agentId));
  }, []);

  const handleRestart = useCallback(async (agentId) => {
    try {
      const token = localStorage.getItem("admin_token") || "";
      const res = await fetch(`/api/v1/admin/agents/${agentId}/restart`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
      const result = await res.json();
      refresh();
      return result;
    } catch {
      return { message: "Restart request failed" };
    }
  }, [refresh]);

  const handleRemove = useCallback(async (agentId) => {
    try {
      const token = localStorage.getItem("admin_token") || "";
      const res = await fetch(`/api/v1/admin/agents/${agentId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ confirm: true, agent_id: agentId }),
      });
      const result = await res.json();
      refresh();
      return result;
    } catch {
      return { message: "Remove request failed" };
    }
  }, [refresh]);

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <div className="border-b border-border">
        <div className="mx-auto max-w-5xl px-5 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-text tracking-tight">
              {data?.plane_name || "CHCA Agents Plane"}
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs text-text-muted font-mono">
              {lastFetched ? `updated ${relativeTime(lastFetched)}` : ""}
            </span>
            <button
              onClick={refresh}
              disabled={loading}
              className="rounded border border-border bg-bg-row px-3 py-1 text-xs font-mono text-text-dim hover:text-text hover:border-text-muted transition-colors disabled:opacity-50"
            >
              {loading ? "..." : "Refresh"}
            </button>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mx-auto max-w-5xl px-5 py-3">
          <div className="rounded border border-status-orange/30 bg-bg-panel px-4 py-2 text-sm text-status-orange font-mono">
            {error}
          </div>
        </div>
      )}

      {/* Agent list */}
      <div className="mx-auto max-w-5xl px-5 py-4">
        {loading && !data && (
          <div className="py-12 text-center text-text-muted font-mono text-sm">
            Loading plane status...
          </div>
        )}

        {data && data.agents.length === 0 && (
          <div className="py-12 text-center text-text-muted font-mono text-sm">
            No agents provisioned yet.
          </div>
        )}

        {data && data.agents.length > 0 && (
          <div className="rounded border border-border bg-bg-panel overflow-hidden">
            {data.agents.map((agent) => (
              <AgentRow
                key={agent.agent_id}
                agent={agent}
                expanded={expandedId === agent.agent_id}
                onToggle={() => handleToggle(agent.agent_id)}
                onRestart={handleRestart}
                onRemove={handleRemove}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

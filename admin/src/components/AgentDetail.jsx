/**
 * AgentDetail — expanded detail panel for a single agent.
 * Shows status, health, memory count, activity, config summary.
 * NEVER shows private config fields or memory contents.
 * Includes action buttons: View Logs, Restart, Remove.
 */

import { useState } from "react";
import HealthBadge from "./HealthBadge";
import LogViewer from "./LogViewer";
import useAgentLogs from "../hooks/useAgentLogs";

function formatDate(iso) {
  if (!iso) return "unknown";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  }) + ", " + d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export default function AgentDetail({ agent, onRestart, onRemove }) {
  const [showLogs, setShowLogs] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [confirmName, setConfirmName] = useState("");
  const [actionMsg, setActionMsg] = useState(null);
  const { logs, loading: logsLoading, error: logsError, fetchLogs, clearLogs } = useAgentLogs();

  const handleViewLogs = () => {
    if (showLogs) {
      setShowLogs(false);
      clearLogs();
    } else {
      setShowLogs(true);
      fetchLogs(agent.agent_id);
    }
  };

  const handleRestart = async () => {
    setActionMsg(null);
    const result = await onRestart(agent.agent_id);
    setActionMsg(result?.message || "Restart requested");
  };

  const handleRemove = async () => {
    if (confirmName !== agent.display_name) return;
    setActionMsg(null);
    const result = await onRemove(agent.agent_id);
    setActionMsg(result?.message || "Remove requested");
    setRemoving(false);
    setConfirmName("");
  };

  const cfg = agent.config_summary || {};
  const mem = agent.memory_count || {};
  const totalMem = (mem.short || 0) + (mem.long || 0);

  return (
    <div className="border-t border-border bg-bg-panel">
      <div className="px-6 py-4 font-mono text-sm leading-7 text-text-dim">
        <div className="mb-1 text-text font-medium">
          {agent.display_name}{" "}
          <span className="text-text-muted text-xs">({agent.agent_id})</span>
        </div>

        <div className="ml-2 border-l border-border pl-4 space-y-0.5">
          <div>
            <span className="text-text-muted">Status:</span>{" "}
            {agent.status} since {formatDate(agent.uptime_since)}
          </div>
          <div>
            <span className="text-text-muted">Health:</span>{" "}
            <HealthBadge health={agent.health} />
          </div>
          <div>
            <span className="text-text-muted">Memory:</span>{" "}
            {totalMem} items{" "}
            <span className="text-text-muted">
              (short: {mem.short || 0}, long: {mem.long || 0})
            </span>
          </div>
          <div>
            <span className="text-text-muted">Activity:</span>{" "}
            {agent.interactions_today} interactions today
          </div>

          {/* Action buttons */}
          <div className="flex gap-2 pt-2">
            <button
              onClick={handleViewLogs}
              className="rounded border border-border bg-bg-row px-3 py-1 text-xs text-text-dim hover:text-text hover:border-text-muted transition-colors"
            >
              {showLogs ? "Hide Logs" : "View Logs"}
            </button>
            <button
              onClick={handleRestart}
              className="rounded border border-border bg-bg-row px-3 py-1 text-xs text-text-dim hover:text-status-yellow hover:border-status-yellow/40 transition-colors"
            >
              Restart
            </button>
            <button
              onClick={() => setRemoving(!removing)}
              className="rounded border border-border bg-bg-row px-3 py-1 text-xs text-text-dim hover:text-status-orange hover:border-status-orange/40 transition-colors"
            >
              {removing ? "Cancel" : "Remove"}
            </button>
          </div>

          {actionMsg && (
            <div className="pt-1 text-xs text-text-muted">{actionMsg}</div>
          )}

          {/* Inline remove confirmation */}
          {removing && (
            <div className="mt-2 rounded border border-status-orange/30 bg-bg-row p-3 text-xs">
              <p className="text-text mb-2">
                Remove {agent.display_name}? This will stop the container.
                Config and memory files are preserved.
              </p>
              <div className="flex items-center gap-2">
                <span className="text-text-muted">
                  Type the agent name to confirm:
                </span>
                <input
                  type="text"
                  value={confirmName}
                  onChange={(e) => setConfirmName(e.target.value)}
                  placeholder={agent.display_name}
                  className="rounded border border-border bg-bg px-2 py-1 text-xs text-text outline-none focus:border-text-muted w-48"
                />
                <button
                  onClick={() => {
                    setRemoving(false);
                    setConfirmName("");
                  }}
                  className="rounded border border-border px-2 py-1 text-text-dim hover:text-text transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRemove}
                  disabled={confirmName !== agent.display_name}
                  className={`rounded border px-2 py-1 transition-colors ${
                    confirmName === agent.display_name
                      ? "border-status-orange/50 text-status-orange hover:bg-status-orange/10"
                      : "border-border text-text-muted cursor-not-allowed"
                  }`}
                >
                  Remove
                </button>
              </div>
            </div>
          )}

          {/* Config summary — non-private only */}
          <div className="pt-2">
            <div className="text-text-muted mb-1">Config (non-private):</div>
            <div className="ml-2 text-text-dim">
              <span className="text-text-muted">Owner:</span>{" "}
              {agent.owner_name}, {agent.role}
              <br />
              {cfg.agent_name && (
                <>
                  <span className="text-text-muted">Agent:</span>{" "}
                  {cfg.agent_name}
                  <br />
                </>
              )}
              <span className="text-text-muted">Energy peak:</span>{" "}
              {cfg.energy_peak || "—"}
              {"  |  "}
              <span className="text-text-muted">Format:</span>{" "}
              {cfg.information_format || "—"}
              {"  |  "}
              <span className="text-text-muted">Checkins:</span>{" "}
              {cfg.morning_checkin || "—"} / {cfg.evening_checkin || "—"}
              {cfg.personality && (
                <>
                  <br />
                  <span className="text-text-muted">Personality:</span>{" "}
                  {cfg.personality}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Log viewer — inline, not modal */}
      {showLogs && (
        <LogViewer
          agentId={agent.agent_id}
          displayName={agent.display_name}
          logs={logs}
          loading={logsLoading}
          error={logsError}
          onClose={() => {
            setShowLogs(false);
            clearLogs();
          }}
          onRefresh={() => fetchLogs(agent.agent_id)}
        />
      )}
    </div>
  );
}

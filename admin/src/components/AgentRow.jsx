/**
 * AgentRow — single agent row in the plane overview.
 * Click to expand/collapse detail panel. No modals.
 */

import StatusDot from "./StatusDot";
import AgentDetail from "./AgentDetail";

function statusColor(status, health) {
  if (health === "healthy" && status === "running") return "green";
  if (status === "starting" || health === "degraded") return "yellow";
  if (status === "degraded") return "orange";
  return "dim";
}

function statusSymbol(status, health) {
  if (health === "healthy" && status === "running") return "\u2713";
  if (status === "starting" || health === "degraded") return "~";
  if (status === "degraded") return "!";
  return "\u25CB";
}

function relativeTime(iso) {
  if (!iso) return "never";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return "yesterday";
}

export default function AgentRow({ agent, expanded, onToggle, onRestart, onRemove }) {
  const color = statusColor(agent.status, agent.health);

  return (
    <div className="border-b border-border last:border-b-0">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-4 px-5 py-3 text-left hover:bg-bg-hover transition-colors group"
      >
        <span
          className={`font-mono text-sm w-5 text-center ${
            color === "green"
              ? "text-status-green"
              : color === "yellow"
                ? "text-status-yellow"
                : color === "orange"
                  ? "text-status-orange"
                  : "text-status-dim"
          }`}
        >
          {statusSymbol(agent.status, agent.health)}
        </span>

        <span className="flex-1 min-w-0">
          <span className="text-sm font-medium text-text truncate">
            {agent.display_name}
          </span>
        </span>

        <span className="font-mono text-xs text-text-muted w-20">
          {agent.status}
        </span>

        <span className="text-xs text-text-dim w-36 hidden sm:block">
          {agent.role}
        </span>

        <span className="text-xs text-text-muted w-32 text-right hidden md:block">
          last active: {relativeTime(agent.last_active)}
        </span>

        <span
          className={`text-xs text-text-muted transition-transform ${
            expanded ? "rotate-90" : ""
          }`}
        >
          {"\u203A"}
        </span>
      </button>

      {expanded && (
        <AgentDetail
          agent={agent}
          onRestart={onRestart}
          onRemove={onRemove}
        />
      )}
    </div>
  );
}

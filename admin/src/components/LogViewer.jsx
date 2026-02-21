/**
 * LogViewer — inline log viewer, expands below agent row.
 * Not a modal — Terminal Calm principle.
 * Shows filtered log lines; sensitive lines already replaced server-side.
 */

import { useEffect, useRef, useState } from "react";

export default function LogViewer({ agentId, displayName, logs, loading, error, onClose, onRefresh }) {
  const bottomRef = useRef(null);
  const [follow, setFollow] = useState(true);

  useEffect(() => {
    if (follow && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, follow]);

  return (
    <div className="mx-4 mb-3 rounded border border-border bg-bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <span className="font-mono text-sm text-text-dim">
          Logs: {displayName}{" "}
          <span className="text-text-muted">(last {logs?.lines?.length || 0} lines)</span>
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => setFollow((f) => !f)}
            className={`rounded px-2 py-0.5 text-xs font-mono transition-colors ${
              follow
                ? "bg-status-green/15 text-status-green"
                : "bg-bg-row text-text-dim hover:text-text"
            }`}
          >
            Follow
          </button>
          <button
            onClick={onRefresh}
            className="rounded bg-bg-row px-2 py-0.5 text-xs font-mono text-text-dim hover:text-text transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={onClose}
            className="rounded bg-bg-row px-2 py-0.5 text-xs font-mono text-text-dim hover:text-text transition-colors"
          >
            Close
          </button>
        </div>
      </div>

      <div className="max-h-64 overflow-y-auto p-3 font-mono text-xs leading-5">
        {loading && (
          <div className="text-text-muted">Loading logs...</div>
        )}
        {error && (
          <div className="text-status-orange">{error}</div>
        )}
        {logs?.lines?.map((line, i) => (
          <div
            key={i}
            className={`${
              line.message.includes("[sensitive")
                ? "text-status-dim italic"
                : "text-text-dim"
            }`}
          >
            <span className="text-text-muted mr-3 select-none">
              {line.timestamp}
            </span>
            {line.message}
          </div>
        ))}
        {logs?.lines?.length === 0 && !loading && (
          <div className="text-text-muted">No log entries</div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

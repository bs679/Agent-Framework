/**
 * Sidebar agent status bar — shows morning/evening check-in status.
 *
 * Placement: below main navigation in the Pulse sidebar.
 *
 * ─────────────────
 *   Agent Check-ins
 *   ✓ Morning  7:02am
 *   ○ Evening  5:00pm
 * ─────────────────
 *
 * Clicking expands to show today's agent summary and alerts inline.
 */

import React, { useState } from "react";
import {
  useCheckinStatus,
  type CheckinStatus,
} from "../../hooks/useAgentApi";

interface AgentStatusBarProps {
  /** Optional summary text from the latest check-in. */
  latestSummary?: string;
  /** Alerts to display in the expanded section. */
  alerts?: Array<{ type: string; message: string; priority: string }>;
}

function formatTime(time: string | null | undefined): string {
  if (!time) return "—";
  // time is "HH:MM" — convert to "H:MMam/pm"
  const [hStr, mStr] = time.split(":");
  const h = parseInt(hStr, 10);
  const suffix = h >= 12 ? "pm" : "am";
  const display = h > 12 ? h - 12 : h === 0 ? 12 : h;
  return `${display}:${mStr}${suffix}`;
}

function StatusIcon({ completed }: { completed: boolean }) {
  return (
    <span
      className={`inline-block w-4 text-center ${
        completed ? "text-green-500" : "text-zinc-500"
      }`}
      aria-label={completed ? "completed" : "pending"}
    >
      {completed ? "✓" : "○"}
    </span>
  );
}

export default function AgentStatusBar({
  latestSummary,
  alerts = [],
}: AgentStatusBarProps) {
  const { status, error } = useCheckinStatus();
  const [expanded, setExpanded] = useState(false);

  if (error) {
    return (
      <div className="border-t border-b border-zinc-700 px-4 py-3 text-xs text-zinc-500">
        Agent status unavailable
      </div>
    );
  }

  if (!status) {
    return (
      <div className="border-t border-b border-zinc-700 px-4 py-3 text-xs text-zinc-500 animate-pulse">
        Loading agent status…
      </div>
    );
  }

  return (
    <div className="border-t border-b border-zinc-700">
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full px-4 py-3 text-left hover:bg-zinc-800 transition-colors"
        aria-expanded={expanded}
      >
        <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">
          Agent Check-ins
        </div>
        <div className="space-y-1 text-sm">
          <div className="flex items-center gap-2 text-zinc-300">
            <StatusIcon completed={status.morning.completed} />
            <span>Morning</span>
            <span className="ml-auto text-zinc-500 text-xs">
              {status.morning.completed
                ? formatTime(status.morning.time)
                : "—"}
            </span>
          </div>
          <div className="flex items-center gap-2 text-zinc-300">
            <StatusIcon completed={status.evening.completed} />
            <span>Evening</span>
            <span className="ml-auto text-zinc-500 text-xs">
              {status.evening.completed
                ? formatTime(status.evening.time)
                : formatTime(status.evening.scheduled_for)}
            </span>
          </div>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-3 text-xs text-zinc-400 border-t border-zinc-800">
          {latestSummary && (
            <p className="mt-2 leading-relaxed">{latestSummary}</p>
          )}
          {alerts.length > 0 && (
            <ul className="mt-2 space-y-1">
              {alerts.map((alert, i) => (
                <li
                  key={i}
                  className={`flex items-start gap-1 ${
                    alert.priority === "high"
                      ? "text-amber-400"
                      : "text-zinc-400"
                  }`}
                >
                  <span className="shrink-0">·</span>
                  <span>{alert.message}</span>
                </li>
              ))}
            </ul>
          )}
          {!latestSummary && alerts.length === 0 && (
            <p className="mt-2 text-zinc-500 italic">
              No check-in summary yet today.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

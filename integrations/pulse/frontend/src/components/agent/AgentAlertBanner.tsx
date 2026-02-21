/**
 * Alert banner — shown at the top of relevant Pulse modules when the
 * agent has flagged urgent items.
 *
 * ┌─────────────────────────────────────────────────────┐
 * │ ~ Your agent flagged 1 item needing attention today  │
 * │   Grievance deadline: Waterbury #24-117 — tomorrow  │
 * │                                        [Dismiss]    │
 * └─────────────────────────────────────────────────────┘
 *
 * Color: amber-700 / dark_orange — NEVER red (Terminal Calm).
 */

import React from "react";

export interface AlertItem {
  type: "deadline" | "urgent_email" | "task_overdue" | "custom";
  message: string;
  priority: "high" | "medium" | "low";
}

interface AgentAlertBannerProps {
  alerts: AlertItem[];
  onDismiss: (message: string) => void;
}

export default function AgentAlertBanner({
  alerts,
  onDismiss,
}: AgentAlertBannerProps) {
  if (alerts.length === 0) return null;

  return (
    <div
      role="alert"
      className="bg-amber-900/40 border border-amber-700/60 rounded-lg px-4 py-3 mb-4"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-amber-300">
            <span className="mr-1">~</span>
            Your agent flagged{" "}
            {alerts.length === 1
              ? "1 item"
              : `${alerts.length} items`}{" "}
            needing attention today
          </p>
          <ul className="mt-1 space-y-0.5">
            {alerts.map((alert, i) => (
              <li
                key={i}
                className="text-sm text-amber-200/80 flex items-center gap-2"
              >
                <span className="text-amber-600 text-xs">
                  {alert.priority === "high" ? "●" : "○"}
                </span>
                {alert.message}
              </li>
            ))}
          </ul>
        </div>
        <button
          onClick={() => alerts.forEach((a) => onDismiss(a.message))}
          className="shrink-0 text-xs text-amber-400 hover:text-amber-200 border border-amber-700/60 rounded px-2 py-1 transition-colors"
          aria-label="Dismiss alerts"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

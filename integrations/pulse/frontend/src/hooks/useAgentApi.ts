/**
 * React hooks for the Pulse agent-plane API.
 *
 * All hooks call /api/v1/agents/* endpoints and handle auth headers.
 */

import { useState, useEffect, useCallback } from "react";

const API_BASE = "/api/v1/agents";

interface FetchOptions {
  method?: string;
  body?: unknown;
}

async function agentFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const token = localStorage.getItem("pulse_token") ?? "";
  const res = await fetch(`${API_BASE}${path}`, {
    method: opts.method ?? "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    throw new Error(`Agent API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ── Types ──────────────────────────────────────────────────────────

export interface CheckinSlotStatus {
  completed: boolean;
  time: string | null;
  scheduled_for?: string | null;
}

export interface CheckinStatus {
  morning: CheckinSlotStatus;
  evening: CheckinSlotStatus;
}

export interface CheckinAlert {
  type: "deadline" | "urgent_email" | "task_overdue" | "custom";
  message: string;
  priority: "high" | "medium" | "low";
}

export interface CaptureResult {
  suggested_action: string;
  details: string;
}

// ── Hooks ──────────────────────────────────────────────────────────

/** Polls agent check-in status for the sidebar. */
export function useCheckinStatus(pollIntervalMs = 60_000) {
  const [status, setStatus] = useState<CheckinStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await agentFetch<CheckinStatus>("/checkin/status");
      setStatus(data);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, pollIntervalMs);
    return () => clearInterval(id);
  }, [refresh, pollIntervalMs]);

  return { status, error, refresh };
}

/** Fetches today's alerts from the latest check-in context. */
export function useAgentAlerts() {
  const [alerts, setAlerts] = useState<CheckinAlert[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    try {
      const ctx = await agentFetch<{ calendar: unknown; tasks: unknown; email: unknown }>(
        "/context"
      );
      // Alerts come from the check-in, not context directly.
      // We fetch status and overlay — real impl would have a dedicated alerts endpoint.
      // For now, we source from localStorage cache of last check-in alerts.
      const cached = localStorage.getItem("pulse_agent_alerts");
      if (cached) {
        setAlerts(JSON.parse(cached) as CheckinAlert[]);
      }
    } catch {
      // silently degrade — alerts are non-critical UI
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const dismiss = useCallback((message: string) => {
    setDismissed((prev) => new Set(prev).add(message));
  }, []);

  const visible = alerts.filter((a) => !dismissed.has(a.message));

  return { alerts: visible, dismiss, refresh };
}

/** Sends a quick-capture note to the agent plane. */
export function useQuickCapture() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CaptureResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const capture = useCallback(async (content: string, agentId: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await agentFetch<CaptureResult>("/capture", {
        method: "POST",
        body: { agent_id: agentId, content, context: "manual" },
      });
      setResult(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { capture, loading, result, error, reset };
}

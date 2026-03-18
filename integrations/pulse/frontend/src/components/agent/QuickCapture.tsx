/**
 * Quick Capture overlay — triggered by ⌘J (Cmd+J / Ctrl+J).
 *
 * Routes input to POST /api/v1/agents/capture instead of creating
 * a task directly.  Shows the suggested action inline below the input.
 */

import React, { useEffect, useRef, useState, useCallback } from "react";
import { useQuickCapture, type CaptureResult } from "../../hooks/useAgentApi";

interface QuickCaptureProps {
  /** The agent ID to send captures to. */
  agentId: string;
  /** Whether the overlay is currently visible. */
  isOpen: boolean;
  /** Called when the overlay should close. */
  onClose: () => void;
}

const ACTION_LABELS: Record<string, string> = {
  create_task: "Create task",
  add_to_memory: "Add to memory",
  reply_email: "Draft reply",
  flag_for_review: "Flag for review",
};

export default function QuickCapture({
  agentId,
  isOpen,
  onClose,
}: QuickCaptureProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState("");
  const { capture, loading, result, error, reset } = useQuickCapture();

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setValue("");
      reset();
      // Small delay to allow DOM mount
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [isOpen, reset]);

  // Global keyboard shortcut: ⌘J / Ctrl+J
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "j") {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Parent handles opening — we just prevent default
          // The parent component should listen for this event
        }
      }
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!value.trim() || loading) return;
      await capture(value.trim(), agentId);
    },
    [value, loading, capture, agentId]
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
        aria-hidden
      />

      {/* Capture panel */}
      <div className="relative w-full max-w-lg bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl overflow-hidden">
        <form onSubmit={handleSubmit}>
          <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-700">
            <span className="text-zinc-500 text-sm font-mono">⌘J</span>
            <input
              ref={inputRef}
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="Quick capture — type a note for your agent…"
              className="flex-1 bg-transparent text-zinc-200 text-sm placeholder-zinc-600 outline-none"
              disabled={loading}
              aria-label="Quick capture input"
            />
            {loading && (
              <span className="text-xs text-zinc-500 animate-pulse">
                Processing…
              </span>
            )}
          </div>
        </form>

        {/* Result display */}
        {result && (
          <div className="px-4 py-3 text-sm border-t border-zinc-800">
            <div className="flex items-center gap-2">
              <span className="text-green-500 text-xs">✓</span>
              <span className="text-zinc-400">
                Suggested action:{" "}
                <span className="text-zinc-200 font-medium">
                  {ACTION_LABELS[result.suggested_action] ??
                    result.suggested_action}
                </span>
              </span>
            </div>
            <p className="mt-1 text-xs text-zinc-500">{result.details}</p>
          </div>
        )}

        {error && (
          <div className="px-4 py-3 text-sm text-amber-400 border-t border-zinc-800">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}

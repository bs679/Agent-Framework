/**
 * Global keyboard shortcut hook for ⌘J / Ctrl+J quick capture.
 *
 * Usage in the root layout:
 *   const { isOpen, open, close } = useQuickCaptureShortcut();
 *   return <QuickCapture isOpen={isOpen} onClose={close} agentId={agentId} />;
 */

import { useCallback, useEffect, useState } from "react";

export function useQuickCaptureShortcut() {
  const [isOpen, setIsOpen] = useState(false);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "j") {
        e.preventDefault();
        toggle();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggle]);

  return { isOpen, open, close };
}

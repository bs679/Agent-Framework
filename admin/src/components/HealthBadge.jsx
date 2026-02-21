/**
 * HealthBadge — status indicator with symbol and label.
 * healthy = green check, degraded = yellow tilde, unreachable = dim circle.
 * NO RED anywhere — Terminal Calm.
 */

const BADGE_CONFIG = {
  healthy: {
    symbol: "\u2713",
    color: "text-status-green",
    label: "healthy",
  },
  degraded: {
    symbol: "~",
    color: "text-status-yellow",
    label: "degraded",
  },
  unreachable: {
    symbol: "\u25CB",
    color: "text-status-dim",
    label: "unreachable",
  },
};

export default function HealthBadge({ health = "unreachable" }) {
  const cfg = BADGE_CONFIG[health] || BADGE_CONFIG.unreachable;
  return (
    <span className={`font-mono text-sm ${cfg.color}`}>
      {cfg.symbol} {cfg.label}
    </span>
  );
}

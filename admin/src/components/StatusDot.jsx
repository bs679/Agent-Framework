/**
 * StatusDot — colored dot indicator.
 * green = healthy/running, yellow = degraded/starting,
 * orange = degraded, dim = stopped/unreachable.
 * NO RED — Terminal Calm design rule.
 */

const COLOR_MAP = {
  green: "bg-status-green shadow-[0_0_6px_var(--color-status-green)]",
  yellow: "bg-status-yellow shadow-[0_0_6px_var(--color-status-yellow)]",
  orange: "bg-status-orange shadow-[0_0_6px_var(--color-status-orange)]",
  dim: "bg-status-dim",
};

export default function StatusDot({ color = "dim" }) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${COLOR_MAP[color] || COLOR_MAP.dim}`}
      aria-label={color}
    />
  );
}

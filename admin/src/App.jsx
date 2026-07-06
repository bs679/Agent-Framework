import React, { useCallback, useEffect, useRef, useState } from 'react';
import { containerPresentation, heartbeatLabel, summarize } from './statusUtils.js';

const API_BASE = import.meta.env.VITE_PULSE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'aios-admin-token';
const REFRESH_MS = 30_000;

async function apiFetch(path, token, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`;
    try {
      const body = await resp.json();
      if (body.detail) detail = body.detail;
    } catch {
      // non-JSON error body — keep the status line
    }
    throw new Error(detail);
  }
  return resp.json();
}

function TokenGate({ onSubmit }) {
  const [value, setValue] = useState('');
  return (
    <div className="token-gate">
      <h1>AIOS Admin Dashboard</h1>
      <p>
        Paste an ADMIN bearer token to connect to the Pulse API at{' '}
        <code>{API_BASE}</code>.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim()) onSubmit(value.trim());
        }}
      >
        <input
          type="password"
          placeholder="Bearer token"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          autoFocus
        />
        <button type="submit">Connect</button>
      </form>
    </div>
  );
}

function StatusBadge({ state }) {
  const p = containerPresentation(state);
  return (
    <span className="badge" style={{ color: p.color, borderColor: p.color }}>
      {p.mark} {p.label}
    </span>
  );
}

function n8nSummary(n8n) {
  if (!n8n || !n8n.enabled) return null;
  if (!n8n.reachable) {
    return { text: 'n8n: unreachable', color: '#cb6d1b' };
  }
  if (n8n.success_rate === null) {
    return { text: `n8n: no finished runs (${n8n.sampled} sampled)`, color: '#9e9e9e' };
  }
  const pct = Math.round(n8n.success_rate * 100);
  const finished = n8n.succeeded + n8n.failed;
  return {
    text: `n8n: ${pct}% success (${n8n.succeeded}/${finished})`,
    color: pct >= 90 ? '#2e7d32' : '#b58900',
  };
}

function SummaryStrip({ agents, dockerAvailable, n8n }) {
  const counts = summarize(agents);
  const n8nInfo = n8nSummary(n8n);
  return (
    <div className="summary">
      <span className="summary-item" style={{ color: '#2e7d32' }}>
        ✓ {counts.running} running
      </span>
      <span className="summary-item" style={{ color: '#b58900' }}>
        ~ {counts.stopped} stopped
      </span>
      <span className="summary-item" style={{ color: '#cb6d1b' }}>
        ! {counts.missing} missing
      </span>
      <span className="summary-item dim">
        {agents.length} total agent{agents.length === 1 ? '' : 's'}
      </span>
      {n8nInfo && (
        <span className="summary-item" style={{ color: n8nInfo.color }}>
          {n8nInfo.text}
        </span>
      )}
      {!dockerAvailable && (
        <span className="summary-item dim">○ docker unreachable from Pulse host</span>
      )}
    </div>
  );
}

function LogsPanel({ agentId, lines, onClose }) {
  return (
    <div className="logs-panel">
      <div className="logs-header">
        <strong>{agentId}</strong> — last {lines.length} log lines
        <button onClick={onClose}>Close</button>
      </div>
      <pre>{lines.length ? lines.join('\n') : '(no output)'}</pre>
    </div>
  );
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '');
  const [agents, setAgents] = useState([]);
  const [dockerAvailable, setDockerAvailable] = useState(true);
  const [n8n, setN8n] = useState(null);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState(null);
  const [logs, setLogs] = useState(null); // {agentId, lines}
  const [busy, setBusy] = useState('');
  const timerRef = useRef(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiFetch('/api/v1/admin/agents', token);
      setAgents(data.agents);
      setDockerAvailable(data.docker_available);
      setError('');
      setLastRefresh(new Date());
      // n8n health is optional — never block the agent table on it
      try {
        setN8n(await apiFetch('/api/v1/admin/n8n/status', token));
      } catch {
        setN8n(null);
      }
    } catch (e) {
      setError(String(e.message || e));
    }
  }, [token]);

  useEffect(() => {
    if (!token) return undefined;
    refresh();
    timerRef.current = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(timerRef.current);
  }, [token, refresh]);

  function connect(newToken) {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
  }

  function disconnect() {
    localStorage.removeItem(TOKEN_KEY);
    setToken('');
    setAgents([]);
    setLogs(null);
  }

  async function showLogs(agentId) {
    setBusy(`logs-${agentId}`);
    try {
      const data = await apiFetch(`/api/v1/admin/agents/${agentId}/logs?tail=200`, token);
      setLogs({ agentId, lines: data.lines });
      setError('');
    } catch (e) {
      setError(`Logs for ${agentId}: ${e.message}`);
    } finally {
      setBusy('');
    }
  }

  async function restart(agentId) {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Restart agent container for ${agentId}?`)) return;
    setBusy(`restart-${agentId}`);
    try {
      await apiFetch(`/api/v1/admin/agents/${agentId}/restart`, token, { method: 'POST' });
      setError('');
      await refresh();
    } catch (e) {
      setError(`Restart ${agentId}: ${e.message}`);
    } finally {
      setBusy('');
    }
  }

  if (!token) return <TokenGate onSubmit={connect} />;

  return (
    <div className="dashboard">
      <header>
        <h1>AIOS Agent Plane</h1>
        <div className="header-right">
          {lastRefresh && (
            <span className="dim">refreshed {lastRefresh.toLocaleTimeString()}</span>
          )}
          <button onClick={refresh}>Refresh</button>
          <button onClick={disconnect}>Disconnect</button>
        </div>
      </header>

      {error && <div className="notice">{error}</div>}

      <SummaryStrip agents={agents} dockerAvailable={dockerAvailable} n8n={n8n} />

      {agents.length === 0 && !error ? (
        <p className="dim">
          No agents registered yet. Provision one with{' '}
          <code>aios agents add --plane &lt;plane&gt; --name &lt;name&gt; --owner &lt;email&gt;</code>.
        </p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Agent</th>
              <th>Owner</th>
              <th>Role</th>
              <th>Plane</th>
              <th>Container</th>
              <th>Morning</th>
              <th>Evening</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.agent_id}>
                <td className="mono">{a.agent_id}</td>
                <td>{a.owner}</td>
                <td>{a.role}</td>
                <td>{a.plane}</td>
                <td>
                  <StatusBadge state={a.container} />
                </td>
                <td>{heartbeatLabel(a.morning_checkin)}</td>
                <td>{heartbeatLabel(a.evening_checkin)}</td>
                <td className="actions">
                  <button
                    disabled={busy === `logs-${a.agent_id}`}
                    onClick={() => showLogs(a.agent_id)}
                  >
                    Logs
                  </button>
                  <button
                    disabled={busy === `restart-${a.agent_id}` || a.container === 'missing'}
                    onClick={() => restart(a.agent_id)}
                  >
                    Restart
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {logs && (
        <LogsPanel agentId={logs.agentId} lines={logs.lines} onClose={() => setLogs(null)} />
      )}
    </div>
  );
}

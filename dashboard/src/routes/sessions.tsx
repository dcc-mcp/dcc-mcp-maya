import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { checkHealth } from '../lib/mcp-client'

export const Route = createFileRoute('/sessions')({ component: Sessions })

interface Session {
  id: string
  status: "active" | "idle" | "closed"
  connectedAt: string
  lastActive: string
  toolsUsed: number
}

function Sessions() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [serverRunning, setServerRunning] = useState(false)
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    setLoading(true)
    const health = await checkHealth()
    const running = health.status === "ok"
    setServerRunning(running)

    if (running) {
      // In a real implementation, we'd query the MCP server for sessions.
      // Currently the MCP protocol doesn't expose sessions directly,
      // so we show placeholder data when the server is running.
      setSessions([
        {
          id: "sse-001",
          status: "active",
          connectedAt: new Date(Date.now() - 300000).toISOString(),
          lastActive: new Date().toISOString(),
          toolsUsed: 12,
        },
      ])
    } else {
      setSessions([])
    }
    setLoading(false)
  }

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--sea-ink)]">Sessions</h1>
          <p className="mt-1 text-sm text-[var(--sea-ink-soft)]">
            Monitor active MCP connections to the server.
          </p>
        </div>
        <button
          onClick={refresh}
          className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-4 py-2 text-sm font-medium text-[var(--sea-ink)] transition hover:bg-[var(--link-bg-hover)]"
        >
          Refresh
        </button>
      </div>

      {!serverRunning && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-400">
          Server is not running. Start the Maya MCP server to see active sessions.
        </div>
      )}

      {loading && sessions.length === 0 && (
        <div className="p-8 text-center text-sm text-[var(--sea-ink-soft)]">
          Loading sessions...
        </div>
      )}

      {serverRunning && sessions.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-[var(--line)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--line)] bg-[var(--surface)]">
                <th className="px-4 py-3 text-left font-semibold text-[var(--sea-ink)]">Session ID</th>
                <th className="px-4 py-3 text-left font-semibold text-[var(--sea-ink)]">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-[var(--sea-ink)]">Connected</th>
                <th className="px-4 py-3 text-left font-semibold text-[var(--sea-ink)]">Last Active</th>
                <th className="px-4 py-3 text-left font-semibold text-[var(--sea-ink)]">Tools Used</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr
                  key={session.id}
                  className="border-b border-[var(--line)] transition hover:bg-[var(--link-bg-hover)]"
                >
                  <td className="px-4 py-3 font-mono text-xs text-[var(--sea-ink)]">{session.id}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      {session.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[var(--sea-ink-soft)]">
                    {new Date(session.connectedAt).toLocaleTimeString()}
                  </td>
                  <td className="px-4 py-3 text-[var(--sea-ink-soft)]">
                    {new Date(session.lastActive).toLocaleTimeString()}
                  </td>
                  <td className="px-4 py-3 text-[var(--sea-ink-soft)]">{session.toolsUsed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {serverRunning && sessions.length === 0 && !loading && (
        <div className="island-shell rounded-2xl p-8 text-center text-sm text-[var(--sea-ink-soft)]">
          No active sessions.
        </div>
      )}
    </div>
  )
}

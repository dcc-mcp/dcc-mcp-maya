import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { configureMCP, checkHealth, getBaseUrl } from '../lib/mcp-client'

export const Route = createFileRoute('/settings')({ component: Settings })

function Settings() {
  const [host, setHost] = useState("127.0.0.1")
  const [port, setPort] = useState("8765")
  const [status, setStatus] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)

  const handleTestConnection = async () => {
    setTesting(true)
    setStatus(null)
    configureMCP(host, parseInt(port, 10))
    try {
      const health = await checkHealth()
      if (health.status === "ok") {
        setStatus("✅ Connection successful!")
      } else {
        setStatus(`⚠️ Server responded: ${health.status}`)
      }
    } catch (err) {
      setStatus(`❌ Connection failed: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      setTesting(false)
    }
  }

  const handleSave = () => {
    configureMCP(host, parseInt(port, 10))
    setStatus("✅ Settings saved. Refreshing dashboard...")
    setTimeout(() => window.location.reload(), 1000)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--sea-ink)]">Settings</h1>
        <p className="mt-1 text-sm text-[var(--sea-ink-soft)]">
          Configure MCP server connection.
        </p>
      </div>

      <section className="island-shell rounded-2xl p-6">
        <h2 className="mb-4 text-lg font-semibold text-[var(--sea-ink)]">Server Connection</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--sea-ink)]">Host</label>
            <input
              type="text"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              className="mt-1 w-full rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-2.5 text-sm text-[var(--sea-ink)] outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/20"
            />
            <p className="mt-1 text-xs text-[var(--sea-ink-soft)]">
              MCP server hostname or IP address
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--sea-ink)]">Port</label>
            <input
              type="number"
              value={port}
              onChange={(e) => setPort(e.target.value)}
              className="mt-1 w-full rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-2.5 text-sm text-[var(--sea-ink)] outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/20"
            />
            <p className="mt-1 text-xs text-[var(--sea-ink-soft)]">
              Default MCP port: 8765
            </p>
          </div>

          {status && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-400">
              {status}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleTestConnection}
              disabled={testing}
              className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-5 py-2.5 text-sm font-medium text-[var(--sea-ink)] transition hover:bg-[var(--link-bg-hover)] disabled:opacity-50"
            >
              {testing ? "Testing..." : "Test Connection"}
            </button>
            <button
              onClick={handleSave}
              className="rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-600"
            >
              Save & Reload
            </button>
          </div>
        </div>
      </section>

      <section className="island-shell rounded-2xl p-6">
        <h2 className="mb-4 text-lg font-semibold text-[var(--sea-ink)]">About</h2>
        <div className="space-y-2 text-sm text-[var(--sea-ink-soft)]">
          <p><strong>Dashboard:</strong> Maya MCP Dashboard v1.0.0</p>
          <p><strong>Framework:</strong> TanStack Start + React 19</p>
          <p>
            <strong>Server API:</strong>{" "}
            <a href={getBaseUrl()} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
              {getBaseUrl()}
            </a>
          </p>
          <p className="mt-4 text-xs">
            This dashboard communicates with the Maya MCP server via the MCP Streamable HTTP protocol.
            The server must be running for the dashboard to function.
          </p>
        </div>
      </section>
    </div>
  )
}

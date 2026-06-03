import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { checkHealth, configureMCP } from '../lib/mcp-client'

export const Route = createFileRoute('/')({ component: Home })

function useMCPStatus() {
  const [status, setStatus] = useState<"connecting" | "running" | "stopped">("connecting")
  const [health, setHealth] = useState<string>("checking...")

  useEffect(() => {
    const check = async () => {
      const h = await checkHealth()
      setHealth(h.status)
      setStatus(h.status === "ok" ? "running" : "stopped")
    }
    check()
    const interval = setInterval(check, 5000)
    return () => clearInterval(interval)
  }, [])

  return { status, health }
}

function Home() {
  const { status, health } = useMCPStatus()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--sea-ink)]">Maya MCP Dashboard</h1>
        <p className="mt-1 text-sm text-[var(--sea-ink-soft)]">
          Monitor and manage your Maya Model Context Protocol server
        </p>
      </div>

      {/* Status Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatusCard
          title="Server Status"
          value={status === "connecting" ? "Connecting..." : status === "running" ? "Running" : "Stopped"}
          icon="🟢"
          accent={status === "running" ? "border-l-emerald-500" : "border-l-amber-500"}
        />
        <StatusCard title="Server Port" value="8765" icon="🔌" accent="border-l-blue-500" />
        <StatusCard title="DCC Type" value="Maya" icon="🎨" accent="border-l-purple-500" />
        <StatusCard title="Health" value={health === "ok" ? "Healthy" : health} icon="❤️" accent={health === "ok" ? "border-l-emerald-500" : "border-l-red-500"} />
      </div>

      {/* Quick Actions */}
      <section className="island-shell rounded-2xl p-6">
        <h2 className="mb-4 text-lg font-semibold text-[var(--sea-ink)]">Quick Actions</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <ActionCard icon="🧩" title="Browse Skills" desc="View and manage installed Maya skills" href="/skills" />
          <ActionCard icon="🔧" title="View Tools" desc="Explore available MCP tools" href="/tools" />
          <ActionCard icon="🔌" title="Sessions" desc="Monitor active connections" href="/sessions" />
        </div>
      </section>

      {/* Info */}
      <section className="island-shell rounded-2xl p-6">
        <h2 className="mb-3 text-lg font-semibold text-[var(--sea-ink)]">Getting Started</h2>
        <div className="space-y-3 text-sm text-[var(--sea-ink-soft)]">
          <p>
            This dashboard connects to the Maya MCP server running on <code>http://127.0.0.1:8765</code>.
          </p>
          <p>
            To start the server, run <code>python -m dcc_mcp_maya</code> or load the Maya plugin.
            The dashboard will automatically detect the server when it's running.
          </p>
          <p>
            You can change the server address in{" "}
            <Link to="/settings" className="font-medium text-emerald-600 underline underline-offset-2 hover:text-emerald-700">
              Settings
            </Link>
            .
          </p>
        </div>
      </section>
    </div>
  )
}

function StatusCard({
  title,
  value,
  icon,
  accent,
}: {
  title: string
  value: string
  icon: string
  accent: string
}) {
  return (
    <div className={`island-shell rounded-xl border-l-4 p-4 ${accent}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--sea-ink-soft)]">
          {title}
        </p>
        <span className="text-lg">{icon}</span>
      </div>
      <p className="mt-2 text-xl font-bold text-[var(--sea-ink)]">{value}</p>
    </div>
  )
}

function ActionCard({
  icon,
  title,
  desc,
  href,
}: {
  icon: string
  title: string
  desc: string
  href: string
}) {
  return (
    <a
      href={href}
      className="feature-card block rounded-xl p-4 no-underline"
    >
      <span className="text-2xl">{icon}</span>
      <h3 className="mt-2 text-sm font-semibold text-[var(--sea-ink)]">{title}</h3>
      <p className="mt-1 text-xs text-[var(--sea-ink-soft)]">{desc}</p>
    </a>
  )
}

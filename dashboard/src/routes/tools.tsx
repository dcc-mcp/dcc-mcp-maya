import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import type { MCPTool } from '../lib/mcp-client'
import { listTools } from '../lib/mcp-client'

export const Route = createFileRoute('/tools')({ component: Tools })

function Tools() {
  const [tools, setTools] = useState<MCPTool[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true)
        const data = await listTools()
        setTools(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch tools")
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  const filtered = tools.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--sea-ink)]">Tools</h1>
        <p className="mt-1 text-sm text-[var(--sea-ink-soft)]">
          Browse available MCP tools exposed by the Maya server.
        </p>
      </div>

      <input
        type="text"
        placeholder="Search tools..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-2.5 text-sm text-[var(--sea-ink)] placeholder:text-[var(--sea-ink-soft)] outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/20"
      />

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="p-8 text-center text-sm text-[var(--sea-ink-soft)]">Loading tools...</div>
      ) : filtered.length === 0 ? (
        <div className="island-shell rounded-2xl p-8 text-center text-sm text-[var(--sea-ink-soft)]">
          {tools.length === 0
            ? "No tools found. Make sure the server is running."
            : "No tools match your search."}
        </div>
      ) : (
        <div className="grid gap-3">
          {filtered.map((tool) => (
            <div
              key={tool.name}
              className="island-shell rounded-xl p-4 transition hover:-translate-y-0.5"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-mono text-sm font-semibold text-[var(--sea-ink)]">
                    {tool.name}
                  </h3>
                  <p className="mt-1 text-xs text-[var(--sea-ink-soft)]">
                    {tool.description || "No description available"}
                  </p>
                </div>
              </div>
              {tool.inputSchema &&
                Object.keys(tool.inputSchema).length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs font-medium text-emerald-600 hover:text-emerald-700">
                      View Parameters ({Object.keys(tool.inputSchema.properties || {}).length})
                    </summary>
                    <pre className="mt-2 overflow-x-auto rounded-lg bg-[var(--sand)] p-3 text-xs text-[var(--sea-ink-soft)]">
                      {JSON.stringify(tool.inputSchema, null, 2)}
                    </pre>
                  </details>
                )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

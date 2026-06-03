/**
 * MCP API client for communicating with the dcc-mcp-maya server.
 *
 * The server runs an MCP Streamable HTTP server on port 8765 (default).
 * This client provides typed access to the MCP protocol endpoints.
 */

// ── Types ────────────────────────────────────────────────────────────────────

export interface MCPTool {
  name: string
  description: string
  inputSchema: Record<string, unknown>
}

export interface SkillInfo {
  name: string
  state: "Discovered" | "Loaded" | "Error"
  description: string
  tool_count: number
  groups: string[]
}

// ── Configuration ────────────────────────────────────────────────────────────

const DEFAULT_HOST = "127.0.0.1"
const DEFAULT_PORT = 8765

let _host = DEFAULT_HOST
let _port = DEFAULT_PORT

export function configureMCP(host: string, port: number) {
  _host = host
  _port = port
}

export function getBaseUrl() {
  return `http://${_host}:${_port}`
}

// ── Generic helpers ──────────────────────────────────────────────────────────

async function mcpRequest<T>(
  method: string,
  params: Record<string, unknown> = {},
): Promise<T> {
  const res = await fetch(`${getBaseUrl()}/mcp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: crypto.randomUUID(),
      method,
      params,
    }),
  })

  if (!res.ok) {
    throw new Error(`MCP request failed: ${res.status} ${res.statusText}`)
  }

  const body = await res.json()
  if (body.error) {
    throw new Error(`MCP error: ${body.error.message} (code ${body.error.code})`)
  }

  return body.result as T
}

// ── Public API ───────────────────────────────────────────────────────────────

/** Check server health. */
export async function checkHealth(): Promise<{ status: string }> {
  try {
    const res = await fetch(`${getBaseUrl()}/health`, { signal: AbortSignal.timeout(3000) })
    if (!res.ok) return { status: "unhealthy" }
    return (await res.json()) as { status: string }
  } catch {
    return { status: "unreachable" }
  }
}

/** Get server status. */
export async function getServerStatus() {
  const health = await checkHealth()
  return {
    status: health.status === "ok" ? "running" as const : "stopped" as const,
    port: _port,
    serverVersion: "0.2.15",
    dccType: "maya",
    uptimeSecs: 0,
  }
}

/** List all available tools via MCP tools/list. */
export async function listTools(): Promise<MCPTool[]> {
  try {
    const result = await mcpRequest<{ tools: MCPTool[] }>("tools/list")
    return result.tools
  } catch {
    return []
  }
}

/** List skills from the MCP server. */
export async function listSkills(): Promise<SkillInfo[]> {
  try {
    const result = await mcpRequest<{ skills: SkillInfo[] }>("skills/list")
    return result.skills
  } catch {
    // Fallback: derive skills from tools list
    const tools = await listTools()
    const skillMap = new Map<string, SkillInfo>()
    for (const tool of tools) {
      const skillName = tool.name.split("__")[0] || tool.name.split("_")[0]
      if (!skillMap.has(skillName)) {
        skillMap.set(skillName, {
          name: skillName,
          state: "Loaded",
          description: tool.description || "",
          tool_count: 0,
          groups: [],
        })
      }
      const entry = skillMap.get(skillName)!
      entry.tool_count++
    }
    return Array.from(skillMap.values())
  }
}

/** Get Prometheus metrics (when enabled). */
export async function getMetrics(): Promise<string> {
  const res = await fetch(`${getBaseUrl()}/metrics`, {
    signal: AbortSignal.timeout(3000),
  })
  if (!res.ok) throw new Error(`Metrics unavailable: ${res.status}`)
  return res.text()
}

/** Load a skill dynamically. */
export async function loadSkill(name: string): Promise<boolean> {
  try {
    await mcpRequest("skills/load", { name })
    return true
  } catch {
    return false
  }
}

/** Call a tool via MCP. */
export async function callTool(
  name: string,
  args: Record<string, unknown> = {},
): Promise<unknown> {
  return mcpRequest("tools/call", { name, arguments: args })
}

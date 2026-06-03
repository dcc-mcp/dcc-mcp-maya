import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import type { SkillInfo } from '../lib/mcp-client'
import { listSkills, loadSkill } from '../lib/mcp-client'

export const Route = createFileRoute('/skills')({ component: Skills })

function Skills() {
  const [skills, setSkills] = useState<SkillInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSkills = async () => {
    try {
      setLoading(true)
      const data = await listSkills()
      setSkills(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch skills")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSkills()
  }, [])

  const handleLoadSkill = async (name: string) => {
    await loadSkill(name)
    await fetchSkills()
  }

  if (loading && skills.length === 0) {
    return <div className="p-8 text-center text-[var(--sea-ink-soft)]">Loading skills...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--sea-ink)]">Skills</h1>
          <p className="mt-1 text-sm text-[var(--sea-ink-soft)]">
            Manage Maya MCP skills. {skills.length} skill(s) available.
          </p>
        </div>
        <button
          onClick={fetchSkills}
          className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-4 py-2 text-sm font-medium text-[var(--sea-ink)] transition hover:bg-[var(--link-bg-hover)]"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {skills.map((skill) => (
          <SkillCard key={skill.name} skill={skill} onLoad={handleLoadSkill} />
        ))}
      </div>

      {skills.length === 0 && !loading && (
        <div className="island-shell rounded-2xl p-8 text-center text-sm text-[var(--sea-ink-soft)]">
          No skills found. Make sure the MCP server is running.
        </div>
      )}
    </div>
  )
}

function SkillCard({
  skill,
  onLoad,
}: {
  skill: SkillInfo
  onLoad: (name: string) => void
}) {
  const isLoaded = skill.state === "Loaded"

  return (
    <div
      className={`island-shell rounded-xl p-4 transition hover:-translate-y-0.5 ${
        isLoaded ? "border-l-4 border-l-emerald-500" : "border-l-4 border-l-amber-400"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-[var(--sea-ink)]">{skill.name}</h3>
          <p className="mt-1 text-xs text-[var(--sea-ink-soft)] line-clamp-2">
            {skill.description || "No description"}
          </p>
        </div>
        <span
          className={`ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
            isLoaded
              ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400"
              : "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400"
          }`}
        >
          {skill.state}
        </span>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-[var(--sea-ink-soft)]">
          {skill.tool_count} tool{skill.tool_count !== 1 ? "s" : ""}
          {skill.groups.length > 0 && ` · ${skill.groups.length} groups`}
        </span>
        {!isLoaded && (
          <button
            onClick={() => onLoad(skill.name)}
            className="rounded-md bg-emerald-500 px-3 py-1 text-xs font-medium text-white transition hover:bg-emerald-600"
          >
            Load
          </button>
        )}
      </div>

      {skill.groups.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {skill.groups.map((group) => (
            <span
              key={group}
              className="rounded-md bg-[var(--chip-bg)] px-1.5 py-0.5 text-xs text-[var(--sea-ink-soft)]"
            >
              {group}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

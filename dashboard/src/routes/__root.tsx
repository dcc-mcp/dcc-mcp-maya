import { HeadContent, Scripts, createRootRoute, Link, Outlet, useLocation } from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'

import appCss from '../styles.css?url'

const NAV_ITEMS = [
  { path: "/", label: "Overview", icon: "📊" },
  { path: "/skills", label: "Skills", icon: "🧩" },
  { path: "/tools", label: "Tools", icon: "🔧" },
  { path: "/sessions", label: "Sessions", icon: "🔌" },
  { path: "/settings", label: "Settings", icon: "⚙️" },
]

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Maya MCP Dashboard" },
    ],
    links: [{ rel: "stylesheet", href: appCss }],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  const location = useLocation()

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <HeadContent />
      </head>
      <body className="font-sans antialiased">
        <div className="flex min-h-screen">
          {/* Sidebar */}
          <aside className="sidebar w-64 flex-shrink-0 border-r border-[var(--line)] bg-[var(--surface)] p-4">
            <div className="mb-8 flex items-center gap-3 px-3 py-2">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-lg font-bold text-white shadow-lg shadow-emerald-500/20">
                M
              </span>
              <div>
                <h1 className="text-sm font-bold text-[var(--sea-ink)]">Maya MCP</h1>
                <p className="text-xs text-[var(--sea-ink-soft)]">Dashboard</p>
              </div>
            </div>

            <nav className="flex flex-col gap-1">
              {NAV_ITEMS.map(({ path, label, icon }) => {
                const isActive = location.pathname === path
                return (
                  <Link
                    key={path}
                    to={path}
                    className={`sidebar-link flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                      isActive
                        ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400"
                        : "text-[var(--sea-ink-soft)] hover:bg-[var(--link-bg-hover)] hover:text-[var(--sea-ink)]"
                    }`}
                  >
                    <span className="text-base">{icon}</span>
                    <span>{label}</span>
                  </Link>
                )
              })}
            </nav>

            <div className="mt-auto border-t border-[var(--line)] pt-4">
              <div className="flex items-center gap-3 rounded-lg px-3 py-2 text-xs text-[var(--sea-ink-soft)]">
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
                Server: 127.0.0.1:8765
              </div>
            </div>
          </aside>

          {/* Main content */}
          <main className="flex-1 overflow-auto">
            <div className="page-wrap px-6 py-6">
              {children}
            </div>
          </main>
        </div>

        <TanStackDevtools config={{ position: "bottom-right" }} plugins={[{ name: "Tanstack Router", render: <TanStackRouterDevtoolsPanel /> }]} />
        <Scripts />
      </body>
    </html>
  )
}

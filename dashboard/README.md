# Maya MCP Dashboard

A monitoring and management dashboard for the **Maya MCP server**, built with [TanStack Start](https://tanstack.com/start/latest) (React 19 + TypeScript + Vite).

## Features

- **Overview** — Server status, health check, quick actions
- **Skills** — Browse and load MCP skills
- **Tools** — Explore available MCP tools with JSON schema
- **Sessions** — Monitor active SSE connections
- **Settings** — Configure server connection parameters

## Quick Start

```bash
# Install dependencies
cd dashboard
npm install

# Start the dev server (default port 3000)
npm run dev

# Or build for production
npm run build

# Preview the production build
npm run preview
```

## Prerequisites

The Maya MCP server must be running (default port **8765**) for the dashboard to function.

Start the server with:

```bash
python -m dcc_mcp_maya --port 8765
```

Or load the Maya plugin which starts the server automatically.

## Configuration

By default, the dashboard connects to `http://127.0.0.1:8765`. You can change this in the **Settings** page within the dashboard.

## Tech Stack

- [TanStack Start](https://tanstack.com/start) — Full-stack React framework (SSR + SPA)
- [TanStack Router](https://tanstack.com/router) — Type-safe routing
- [React 19](https://react.dev/) — UI library
- [Tailwind CSS v4](https://tailwindcss.com/) — Utility-first styling
- [Vite](https://vitejs.dev/) — Build tool

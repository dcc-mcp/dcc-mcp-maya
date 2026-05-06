import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'dcc-mcp-maya',
  description: 'AI-Powered Maya Automation via MCP Protocol',
  base: '/',

  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }],
  ],

  locales: {
    root: {
      label: 'English',
      lang: 'en',
    },
    zh: {
      label: '中文',
      lang: 'zh-CN',
      link: '/zh/',
      themeConfig: {
        nav: [
          { text: '指南', link: '/zh/guide/' },
          { text: 'API 参考', link: '/zh/api/actions' },
          { text: 'GitHub', link: 'https://github.com/loonghao/dcc-mcp-maya' },
        ],
        sidebar: {
          '/zh/guide/': [
            {
              text: '入门',
              items: [
                { text: '简介', link: '/zh/guide/' },
                { text: '快速开始', link: '/zh/guide/getting-started' },
                { text: '安装指南', link: '/zh/guide/installation' },
              ],
            },
            {
              text: '使用指南',
              items: [
                { text: 'MCP Tools 指南', link: '/zh/guide/mcp-tools' },
                { text: 'Action 完整列表', link: '/zh/guide/actions' },
                { text: '截图与快照', link: '/zh/guide/snapshot' },
                { text: '场景信息查询', link: '/zh/guide/scene' },
                { text: '多实例部署', link: '/zh/guide/multi-instance' },
                { text: '退出场景安全矩阵', link: '/zh/guide/shutdown-matrix' },
                { text: '贡献技能', link: '/zh/guide/contributing' },
                { text: '高级用法', link: '/zh/guide/advanced' },
              ],
            },
          ],
          '/zh/api/': [
            {
              text: 'API 参考',
              items: [
                { text: 'Action API', link: '/zh/api/actions' },
                { text: 'MayaMcpServer', link: '/zh/api/adapter' },
                { text: '截图 API', link: '/zh/api/snapshot' },
                { text: '场景信息 API', link: '/zh/api/scene' },
              ],
            },
          ],
        },
        footer: {
          message: '基于 MIT 许可证发布',
          copyright: 'Copyright © 2024-present Long Hao',
        },
      },
    },
  },

  themeConfig: {
    logo: '/logo.svg',

    nav: [
      { text: 'Guide', link: '/guide/' },
      { text: 'API Reference', link: '/api/actions' },
      { text: 'GitHub', link: 'https://github.com/loonghao/dcc-mcp-maya' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/guide/' },
            { text: 'Quick Start', link: '/guide/getting-started' },
            { text: 'Installation', link: '/guide/installation' },
          ],
        },
        {
          text: 'Usage',
          items: [
            { text: 'MCP Tools Guide', link: '/guide/mcp-tools' },
            { text: 'Action List', link: '/guide/actions' },
            { text: 'Viewport Snapshot', link: '/guide/snapshot' },
            { text: 'Scene Info', link: '/guide/scene' },
            { text: 'Multi-Instance Deployment', link: '/guide/multi-instance' },
            { text: 'Shutdown Safety Matrix', link: '/guide/shutdown-matrix' },
            { text: 'Contributing Skills', link: '/guide/contributing' },
            { text: 'Advanced Usage', link: '/guide/advanced' },
          ],
        },
      ],
      '/api/': [
        {
          text: 'API Reference',
          items: [
            { text: 'Action API', link: '/api/actions' },
            { text: 'MayaMcpServer', link: '/api/adapter' },
            { text: 'Snapshot API', link: '/api/snapshot' },
            { text: 'Scene API', link: '/api/scene' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/loonghao/dcc-mcp-maya' },
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024-present Long Hao',
    },

    search: {
      provider: 'local',
    },
  },
})

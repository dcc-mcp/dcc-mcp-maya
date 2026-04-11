import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'dcc-mcp-maya',
  description: 'AI-Powered Maya Automation via MCP Protocol',
  base: '/dcc-mcp-maya/',
  head: [
    ['link', { rel: 'icon', href: '/dcc-mcp-maya/favicon.ico' }],
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
          { text: 'API', link: '/zh/api/actions' },
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
                { text: 'Action 列表', link: '/zh/guide/actions' },
                { text: 'MCP Tools', link: '/zh/guide/mcp-tools' },
                { text: '高级用法', link: '/zh/guide/advanced' },
                { text: '贡献自定义技能包', link: '/zh/guide/contributing' },
              ],
            },
          ],
          '/zh/api/': [
            {
              text: 'API 参考',
              items: [
                { text: 'Actions', link: '/zh/api/actions' },
                { text: 'MayaMcpServer', link: '/zh/api/server' },
              ],
            },
          ],
        },
      },
    },
  },

  themeConfig: {
    logo: '/logo.svg',
    nav: [
      { text: 'Guide', link: '/guide/' },
      { text: 'API', link: '/api/actions' },
      {
        text: 'v0.3.0',
        items: [
          { text: 'Changelog', link: 'https://github.com/loonghao/dcc-mcp-maya/blob/main/CHANGELOG.md' },
          { text: 'PyPI', link: 'https://pypi.org/project/dcc-mcp-maya/' },
        ],
      },
      { text: 'GitHub', link: 'https://github.com/loonghao/dcc-mcp-maya' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Introduction',
          items: [
            { text: 'What is dcc-mcp-maya?', link: '/guide/' },
            { text: 'Getting Started', link: '/guide/getting-started' },
            { text: 'Installation', link: '/guide/installation' },
          ],
        },
        {
          text: 'Guides',
          items: [
            { text: 'Available Actions', link: '/guide/actions' },
            { text: 'MCP Tools for Agents', link: '/guide/mcp-tools' },
            { text: 'Advanced Usage', link: '/guide/advanced' },
            { text: 'Contributing a Skill', link: '/guide/contributing' },
          ],
        },
      ],
      '/api/': [
        {
          text: 'API Reference',
          items: [
            { text: 'Actions', link: '/api/actions' },
            { text: 'MayaMcpServer', link: '/api/server' },
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

    editLink: {
      pattern: 'https://github.com/loonghao/dcc-mcp-maya/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },

    search: {
      provider: 'local',
    },
  },
})

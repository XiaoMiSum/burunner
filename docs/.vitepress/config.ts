import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'burunner',
  description: 'Natural language browser testing framework based on browser-use',
  base: '/burunner/',

  locales: {
    root: {
      label: 'English',
      lang: 'en',
    },
    zh: {
      label: '简体中文',
      lang: 'zh-CN',
      themeConfig: {
        nav: [
          { text: '指南', link: '/zh/guide/getting-started' },
          { text: '开发', link: '/zh/development/contributing' },
          {
            text: 'GitHub',
            link: 'https://github.com/browser-use/browser-use-runner',
          },
        ],
        sidebar: {
          '/zh/guide/': [
            {
              text: '使用指南',
              items: [
                { text: '快速开始', link: '/zh/guide/getting-started' },
                { text: '安装', link: '/zh/guide/installation' },
                { text: '配置', link: '/zh/guide/configuration' },
              ],
            },
            {
              text: '用例编写',
              items: [
                { text: '用例编写', link: '/zh/guide/writing-cases' },
                { text: '预设', link: '/zh/guide/presets' },
                { text: '变量', link: '/zh/guide/variables' },
                { text: '数据驱动测试', link: '/zh/guide/data-driven' },
                { text: '多环境配置', link: '/zh/guide/environments' },
              ],
            },
            {
              text: '运行与报告',
              items: [
                { text: 'CLI', link: '/zh/guide/cli' },
                { text: '报告', link: '/zh/guide/reporting' },
                { text: '通知配置', link: '/zh/guide/notifications' },
              ],
            },
          ],
          '/zh/development/': [
            {
              text: '开发指南',
              items: [
                { text: '贡献指南', link: '/zh/development/contributing' },
                { text: '架构概览', link: '/zh/development/architecture' },
                { text: '扩展开发', link: '/zh/development/extending' },
              ],
            },
          ],
        },
      },
    },
  },

  themeConfig: {
    search: {
      provider: 'local',
    },

    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'Development', link: '/development/contributing' },
      {
        text: 'GitHub',
        link: 'https://github.com/browser-use/browser-use-runner',
      },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Guide',
          items: [
            { text: 'Getting Started', link: '/guide/getting-started' },
            { text: 'Installation', link: '/guide/installation' },
            { text: 'Configuration', link: '/guide/configuration' },
          ],
        },
        {
          text: 'Writing Cases',
          items: [
            { text: 'Writing Cases', link: '/guide/writing-cases' },
            { text: 'Presets', link: '/guide/presets' },
            { text: 'Variables', link: '/guide/variables' },
            { text: 'Data-Driven Testing', link: '/guide/data-driven' },
            { text: 'Environments', link: '/guide/environments' },
          ],
        },
        {
          text: 'Running',
          items: [
            { text: 'CLI', link: '/guide/cli' },
            { text: 'Reporting', link: '/guide/reporting' },
            { text: 'Notifications', link: '/guide/notifications' },
          ],
        },
      ],
      '/development/': [
        {
          text: 'Development',
          items: [
            { text: 'Contributing', link: '/development/contributing' },
            { text: 'Architecture', link: '/development/architecture' },
            { text: 'Extending', link: '/development/extending' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/browser-use/browser-use-runner' },
    ],
  },
})

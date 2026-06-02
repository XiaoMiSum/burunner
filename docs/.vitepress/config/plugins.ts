import type { MarkdownRenderer } from 'vitepress'
import mermaid from 'mermaid'

let initialized = false

export function mdPlugin(md: MarkdownRenderer) {
  // 初始化 mermaid
  if (!initialized) {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
    })
    initialized = true
  }

  // 保存默认的 fence 渲染器
  const defaultRender = md.renderer.rules.fence!

  md.renderer.rules.fence = (tokens, idx, options, env, self) => {
    const token = tokens[idx]
    const code = token.content.trim()
    
    // 检查是否为 mermaid 代码块
    if (token.info === 'mermaid') {
      // 生成唯一 ID
      const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      
      // 返回渲染 mermaid 的 HTML
      return `<div class="mermaid" id="${id}">${code}</div>`
    }
    
    // 其他代码块使用默认渲染
    return defaultRender(tokens, idx, options, env, self)
  }
}

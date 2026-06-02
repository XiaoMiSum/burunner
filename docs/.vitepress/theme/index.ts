import DefaultTheme from 'vitepress/theme'
import { useRoute } from 'vitepress'
import { nextTick, onMounted, watch } from 'vue'
import mermaid from 'mermaid'
import './custom.css'

export default {
  extends: DefaultTheme,
  setup() {
    const route = useRoute()
    
    onMounted(async () => {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose',
      })
      await renderMermaid()
    })
    
    watch(
      () => route.path,
      async () => {
        await nextTick()
        await renderMermaid()
      }
    )
  },
}

async function renderMermaid() {
  const elements = document.querySelectorAll('.mermaid')
  if (elements.length === 0) return
  
  for (const element of Array.from(elements)) {
    if (element.querySelector('svg')) continue
    
    const code = element.textContent || ''
    if (!code) continue
    
    try {
      const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`
      const { svg } = await mermaid.render(id, code)
      element.innerHTML = svg
    } catch (error) {
      console.error('Mermaid render error:', error)
      element.innerHTML = `<pre style="color: red;">Mermaid error: ${error}</pre>`
    }
  }
}

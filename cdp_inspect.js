// Inspect the operator page via CDP: AI DJ strip state + internal screenshot
const WebSocket = require('ws')
const fs = require('fs')

const listUrl = 'http://127.0.0.1:9224/json/list'
fetch(listUrl).then(r => r.json()).then(list => {
  const page = list.find(t => t.type === 'page')
  if (!page) { console.error('no page target'); process.exit(1) }
  const ws = new WebSocket(page.webSocketDebuggerUrl)
  let id = 0
  const pending = {}
  function send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const mid = ++id
      pending[mid] = { resolve, reject }
      ws.send(JSON.stringify({ id: mid, method, params }))
    })
  }
  ws.on('message', (data) => {
    const msg = JSON.parse(data)
    if (msg.id && pending[msg.id]) {
      pending[msg.id].resolve(msg.result)
      delete pending[msg.id]
    }
  })
  ws.on('open', async () => {
    await send('Runtime.enable')
    await send('Page.enable')
    // 1) Evaluasi strip
    const expr = `(() => {
      const strip = document.querySelector('.ai-dj-strip')
      const chips = document.querySelectorAll('.ai-dj-chip')
      const rect = strip ? strip.getBoundingClientRect() : null
      const first = chips[0]
      const fr = first ? first.getBoundingClientRect() : null
      const cs = first ? getComputedStyle(first) : null
      return JSON.stringify({
        stripExists: !!strip,
        chipCount: chips.length,
        stripRect: rect ? { x: rect.x, y: rect.y, w: rect.width, h: rect.height } : null,
        firstChipRect: fr ? { x: fr.x, y: fr.y, w: fr.width, h: fr.height } : null,
        firstChipDisplay: cs ? cs.display : null,
        firstChipVisibility: cs ? cs.visibility : null,
        firstChipBg: cs ? cs.background : null,
        firstChipText: first ? first.textContent.trim().slice(0, 40) : null,
        activeTab: document.querySelector('.tab-btn.active')?.textContent.trim(),
        viewportH: window.innerHeight
      })
    })()`
    const ev = await send('Runtime.evaluate', { expression: expr, returnByValue: true })
    console.log('STRIP:', ev.result.value)
    // 2) Screenshot internal
    const shot = await send('Page.captureScreenshot', { format: 'png' })
    fs.writeFileSync('/tmp/cdp_internal.png', Buffer.from(shot.data, 'base64'))
    console.log('SCREENSHOT: /tmp/cdp_internal.png', shot.data.length, 'bytes base64')
    ws.close(); process.exit(0)
  })
  ws.on('error', (e) => { console.error('ws error', e.message); process.exit(1) })
}).catch(e => { console.error('fetch error', e.message); process.exit(1) })

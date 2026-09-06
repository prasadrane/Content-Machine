export async function streamSSE(url, payload, dispatch) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}))
    throw new Error(errData.detail || `Server returned ${res.status}`)
  }

  if (!res.body) {
    throw new Error('ReadableStream not supported by response')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let currentEvent = null
  let isComplete = false

  while (!isComplete) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || '' // keep uncompleted partial line

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) {
        currentEvent = null
        continue
      }
      if (trimmed.startsWith('event:')) {
        currentEvent = trimmed.replace(/^event:\s*/, '').trim()
      } else if (trimmed.startsWith('data:')) {
        const jsonStr = trimmed.replace(/^data:\s*/, '').trim()
        try {
          const data = JSON.parse(jsonStr)
          dispatch(currentEvent, data)
          if (currentEvent === 'complete') {
            isComplete = true
            reader.cancel().catch(() => {})
            break
          }
        } catch (err) {
          console.error('Failed to parse SSE JSON:', err, jsonStr)
        }
      }
    }
  }
}

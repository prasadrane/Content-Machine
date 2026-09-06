import { describe, it, expect, vi, afterEach } from 'vitest'
import { streamSSE } from './sse'
import { getOracleHistory, runOracleScan } from './oracle'

afterEach(() => vi.unstubAllGlobals())

function streamResponse(text, ok = true, status = 200) {
  const encoder = new TextEncoder()
  const body = new ReadableStream({
    start(c) { c.enqueue(encoder.encode(text)); c.close() },
  })
  // json() present so the verbatim !ok path (`res.json().catch(() => ({}))`) resolves
  return { ok, status, body, json: async () => ({}) }
}

describe('streamSSE', () => {
  it('dispatches event/data frame pairs', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      streamResponse('event: phase\ndata: {"step":1}\n\nevent: done\ndata: {"ok":true}\n\n')))
    const events = []
    await streamSSE('/api/oracle/scan-stream', { q: 1 }, (name, data) => events.push([name, data]))
    expect(events).toEqual([['phase', { step: 1 }], ['done', { ok: true }]])
    expect(fetch.mock.calls[0][1].method).toBe('POST')
    expect(fetch.mock.calls[0][1].body).toBe('{"q":1}')
  })
  it('handles frames split across chunks', async () => {
    const encoder = new TextEncoder()
    const body = new ReadableStream({
      start(c) {
        c.enqueue(encoder.encode('event: tick\nda'))
        c.enqueue(encoder.encode('ta: {"n":2}\n\n'))
        c.close()
      },
    })
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, body })))
    const events = []
    await streamSSE('/u', {}, (name, data) => events.push([name, data]))
    expect(events).toEqual([['tick', { n: 2 }]])
  })
  it('throws on !ok response', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => streamResponse('', false, 500)))
    await expect(streamSSE('/u', {}, () => {})).rejects.toThrow(/500/)
  })
})

describe('getOracleHistory', () => {
  // Mirrors fetchArchive construction: params appended in order topic, verdict, search.
  it('builds querystring from params', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ items: [] }) })))
    await getOracleHistory({ topic: 'Systems', verdict: 'maybe', search: 'k8s' })
    expect(fetch.mock.calls[0][0]).toBe('/api/oracle/history?topic=Systems&verdict=maybe&search=k8s')
  })
  it('omits empty params', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ items: [] }) })))
    await getOracleHistory({})
    expect(fetch.mock.calls[0][0]).toBe('/api/oracle/history?')
  })
})

describe('runOracleScan', () => {
  it('POSTs payload to scan-stream and dispatches frames', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      streamResponse('event: complete\ndata: {"passed":2}\n\n')))
    const events = []
    await runOracleScan({ limit: 15 }, (name, data) => events.push([name, data]))
    expect(fetch.mock.calls[0][0]).toBe('/api/oracle/scan-stream')
    expect(fetch.mock.calls[0][1].method).toBe('POST')
    expect(events).toEqual([['complete', { passed: 2 }]])
  })
})

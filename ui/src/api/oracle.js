import { fetchJson } from './client'
import { streamSSE } from './sse'

export function runOracleScan(payload, dispatch) {
  return streamSSE('/api/oracle/scan-stream', payload, dispatch)
}

export function getOracleHistory(params) {
  return fetchJson(`/api/oracle/history?${new URLSearchParams(params)}`)
}

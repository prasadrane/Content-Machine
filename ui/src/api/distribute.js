import { fetchJson } from './client'

export function runDistribute(payload) {
  return fetchJson('/api/distribute/run', { method: 'POST', body: payload })
}

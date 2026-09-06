import { fetchJson } from './client'

export function runHumanize(payload) {
  return fetchJson('/api/humanize', { method: 'POST', body: payload })
}

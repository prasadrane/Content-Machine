import { fetchJson } from './client'

export function runCouncil(payload) {
  return fetchJson('/api/council/run', { method: 'POST', body: payload })
}

export function getCouncilHistory(slug) {
  return fetchJson(`/api/council/history/${encodeURIComponent(slug)}`)
}

export function getCouncilSpikes() {
  return fetchJson('/api/council/spikes')
}

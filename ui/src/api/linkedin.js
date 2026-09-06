import { fetchJson } from './client'

export function getLinkedInStatus() {
  return fetchJson('/api/linkedin/status')
}

export function syncLinkedIn(payload) {
  return fetchJson('/api/linkedin/sync', { method: 'POST', body: payload })
}

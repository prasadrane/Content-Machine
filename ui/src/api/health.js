import { fetchJson } from './client'

export function getHealth() {
  return fetchJson('/api/health')
}

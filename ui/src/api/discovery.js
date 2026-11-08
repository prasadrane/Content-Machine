import { fetchJson } from './client'

export const refreshDiscovery = () => fetchJson('/api/workflow/discovery/refresh', { method: 'POST' })

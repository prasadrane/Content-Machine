import { fetchJson } from './client'

// Identity comes from the current verified session, never browser owner fields.
export const bootstrapGuest = () => fetchJson('/api/workflow/guest/bootstrap', { method: 'POST', body: {} })

export const previewGuestTransfer = guestToken => fetchJson('/api/workflow/guest/transfer/preview', {
  method: 'POST', body: {}, headers: { 'X-Guest-Authorization': `Bearer ${guestToken}` },
})
export const transferGuest = (guestToken, fingerprint, requestId) => fetchJson('/api/workflow/guest/transfer', {
  method: 'POST', body: { consent: true, source_fingerprint: fingerprint },
  headers: { 'X-Guest-Authorization': `Bearer ${guestToken}`, 'Idempotency-Key': requestId },
})
export const getGuestTransfer = transferId => fetchJson(`/api/workflow/guest/transfers/${encodeURIComponent(transferId)}`)

import { afterEach, expect, it, vi } from 'vitest'
import { clearGuestProof, readGuestProof, retainGuestProof } from './guestProof'
afterEach(() => { sessionStorage.clear(); vi.useRealTimers() })
it('bounds guest proof retention to ten minutes and drops expired data', () => {
  vi.useFakeTimers(); vi.setSystemTime(1000000)
  retainGuestProof({ user: { id: 'g', is_anonymous: true }, access_token: 'proof', expires_at: 999999 })
  expect(readGuestProof()).toMatchObject({ token: 'proof', owner: 'g', expires: 1600000 })
  vi.advanceTimersByTime(600001)
  expect(readGuestProof()).toBeNull()
  expect(sessionStorage.length).toBe(0)
})
it('requires an unexpired anonymous session and handles unavailable storage', () => {
  expect(() => retainGuestProof({ user: { id: 'creator' }, access_token: 'x' })).toThrow()
  expect(() => retainGuestProof({ user: { id: 'g', is_anonymous: true }, access_token: 'x', expires_at: 1 })).toThrow()
  sessionStorage.setItem('cm.guest-copy-proof.v1', 'bad json')
  expect(readGuestProof()).toBeNull()
  clearGuestProof()
})

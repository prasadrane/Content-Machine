// A one-tab OAuth handoff, only after explicit user action. Never put proof in
// a URL, persistent localStorage, UI text, analytics or a transfer receipt.
const KEY = 'cm.guest-copy-proof.v1'
const MAX_AGE = 10 * 60 * 1000
export function clearGuestProof() { try { sessionStorage.removeItem(KEY) } catch { /* storage unavailable */ } }
export function readGuestProof() {
  try {
    const proof = JSON.parse(sessionStorage.getItem(KEY))
    if (typeof proof?.token === 'string' && proof.token && typeof proof.owner === 'string' &&
        typeof proof.requestId === 'string' && Number.isFinite(proof.expires) &&
        proof.expires > Date.now() && proof.expires <= Date.now() + MAX_AGE) return proof
  } catch { /* malformed or disabled storage */ }
  clearGuestProof()
  return null
}
export function retainGuestProof(session) {
  clearGuestProof()
  const expires = Math.min(Number(session?.expires_at) * 1000, Date.now() + MAX_AGE)
  if (session?.user?.is_anonymous !== true || !session.user.id || !session.access_token || !(expires > Date.now())) {
    throw new Error('Your guest session expired. Sign in as a guest again before copying.')
  }
  const proof = { token: session.access_token, owner: session.user.id, expires, requestId: crypto.randomUUID() }
  try { sessionStorage.setItem(KEY, JSON.stringify(proof)) } catch {
    throw new Error('This browser cannot preserve the guest session during sign-in. Enable session storage to copy guest work.')
  }
  return proof
}

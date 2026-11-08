import React, { useEffect, useRef, useState } from 'react'
import { previewGuestTransfer, transferGuest } from '../../api/guests'
import { clearGuestProof, readGuestProof } from './guestProof'
import { GuestReceipt } from './GuestReceipt'

export function GuestTransfer({ session }) {
  const [proof, setProof] = useState(readGuestProof)
  const [preview, setPreview] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState('')
  const [consent, setConsent] = useState(false)
  const [pending, setPending] = useState(false)
  const [done, setDone] = useState(false)
  const [receiptId, setReceiptId] = useState(null)
  const inFlight = useRef(false)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])
  useEffect(() => {
    if (!proof) return undefined
    let active = true
    const forget = () => {
      clearGuestProof()
      if (!inFlight.current) {
        setProof(null)
        setError('The guest copy session expired. Start again from the guest workspace to copy its work.')
      }
    }
    const remaining = proof.expires - Date.now()
    if (remaining <= 0 || proof.owner === session.user.id) { forget(); return undefined }
    const timer = window.setTimeout(forget, remaining)
    setPreview(null); setConsent(false); setError('')
    previewGuestTransfer(proof.token).then(result => { if (active) setPreview(result) })
      .catch(() => { if (active) setError('Guest copy preview is unavailable. Retry before copying.') })
    return () => { active = false; window.clearTimeout(timer) }
  }, [proof, session.user.id, attempt])
  if (done) return <section className="cm-panel">
    <p role="status">Guest work copied. Copies require a new approval before export.</p>
    {receiptId && <GuestReceipt transferId={receiptId} />}
  </section>
  if (!proof) return error ? <p role="alert">{error}</p> : null
  const copy = async () => {
    if (inFlight.current || !consent || !preview) return
    if (!readGuestProof()) {
      setProof(null); setError('The guest copy session expired. Start again from the guest workspace to copy its work.')
      return
    }
    inFlight.current = true
    setPending(true); setError('')
    try {
      const result = await transferGuest(proof.token, preview.source_fingerprint, proof.requestId)
      if (!mounted.current) return
      setReceiptId(typeof result?.transfer_id === 'string' ? result.transfer_id : null)
      clearGuestProof(); setProof(null); setDone(true)
      window.dispatchEvent(new Event('cm:guest-work-copied'))
    } catch (failure) {
      if (!mounted.current) return
      if (proof.expires <= Date.now()) {
        clearGuestProof(); setProof(null)
        setError('Guest copy outcome could not be confirmed. Check saved work before starting another copy; the guest session has expired.')
      } else if (failure.body?.code === 'transfer_source_changed') {
        setConsent(false); setAttempt(value => value + 1)
      } else setError('Guest copy outcome could not be confirmed. Retry with the same request; existing copies will be preserved.')
    } finally { inFlight.current = false; if (mounted.current) setPending(false) }
  }
  return <section className="cm-panel" aria-label="Guest copy">
    <h2 className="cm-panel-title">Copy guest work into your account</h2>
    <p>The guest workspace stays unchanged. Current drafts become new unapproved copies. Original history is archived separately; existing account settings stay unchanged.</p>
    {preview ? <>
      <p>{preview.item_count} items available to copy.</p>
      <label className="cm-label"><input type="checkbox" checked={consent} disabled={pending} onChange={event => setConsent(event.target.checked)} /> I consent to new unapproved copies that require approval again.</label>
      <button type="button" className="cm-button cm-button-primary" disabled={pending || !consent} onClick={copy}>Copy into my workspace</button>
    </> : !error && <p role="status">Preparing guest copy preview…</p>}
    {error && <><p role="alert">{error}</p><button type="button" className="cm-button cm-button-secondary" disabled={pending} onClick={() => preview ? copy() : setAttempt(value => value + 1)}>Retry guest copy</button></>}
    <button type="button" className="cm-button cm-button-quiet" disabled={pending} onClick={() => { clearGuestProof(); setProof(null) }}>Skip guest copy</button>
  </section>
}

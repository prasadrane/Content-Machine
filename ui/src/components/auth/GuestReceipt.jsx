import React, { useEffect, useRef, useState } from 'react'
import { getGuestTransfer } from '../../api/guests'

export function GuestReceipt({ transferId }) {
  const [receipt, setReceipt] = useState(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const generation = useRef(0)
  const inFlight = useRef(false)
  useEffect(() => {
    generation.current += 1
    setReceipt(null); setError(''); setPending(false); inFlight.current = false
    return () => { generation.current += 1 }
  }, [transferId])
  const load = async () => {
    if (inFlight.current) return
    const current = generation.current
    inFlight.current = true; setPending(true); setError('')
    try {
      const value = await getGuestTransfer(transferId)
      if (current !== generation.current) return
      if (value?.transfer_id !== transferId || value.editorial_approval !== false ||
          !Array.isArray(value.archive?.tables?.workflow_items)) throw new Error('Invalid receipt')
      setReceipt(value)
    } catch {
      if (current === generation.current) setError('Could not load archived history. You can retry viewing it.')
    } finally {
      if (current === generation.current) { inFlight.current = false; setPending(false) }
    }
  }
  const tables = receipt?.archive.tables
  const count = table => Array.isArray(tables?.[table]) ? tables[table].length : 0
  return <section className="cm-subpanel" aria-label="Copied guest history">
    <button type="button" className="cm-button cm-button-secondary" disabled={pending} onClick={load}>View copied history</button>
    {pending && <p role="status">Loading archived guest history…</p>}
    {error && <p role="alert">{error}</p>}
    {receipt && <>
      <h3 className="cm-panel-title">Archived original guest history</h3>
      <p>This read-only archive records the guest workspace at copy time. Copies require new review and approval. Archived settings are inactive.</p>
      <p>{count('workflow_items')} source items; {count('workflow_versions')} archived versions; {count('workflow_reviews')} archived reviews; {count('workflow_operations')} archived AI operations.</p>
      <p>{count('workflow_approvals')} historical approvals are inert and grant no approval to the new copies.</p>
      <ul>{tables.workflow_items.slice(0, 20).map((item, index) => <li key={index}>{String(item.title || 'Untitled guest item').slice(0, 160)}</li>)}</ul>
      {tables.workflow_items.length > 20 && <p>Showing the first 20 of {tables.workflow_items.length} source items.</p>}
    </>}
  </section>
}

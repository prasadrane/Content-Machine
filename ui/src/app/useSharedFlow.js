import { useCallback, useId, useRef, useState } from 'react'

export function useSharedFlow(setActiveTab) {
  const sessionId = useId()
  const sequence = useRef(0)
  const [council, setCouncil] = useState({ itemId: `${sessionId}-council`, version: 1, text: '', slug: 'spike-1' })
  const councilRef = useRef(council)
  const [distributeAnchor, setDistributeAnchor] = useState(null)
  const anchorRef = useRef(null)
  // Session-only authority. Exact text alone cannot identify an approval.
  const [approval, setApproval] = useState(null)

  const invalidateApproval = useCallback(() => setApproval(null), [])
  const newItemId = useCallback(() => `${sessionId}-item-${++sequence.current}`, [sessionId])

  const updateCouncil = useCallback((field, value) => {
    const current = councilRef.current
    const nextValue = typeof value === 'function' ? value(current[field]) : value
    if (nextValue === current[field]) return
    const next = { ...current, [field]: nextValue, version: current.version + 1 }
    councilRef.current = next
    setCouncil(next)
    invalidateApproval()
  }, [invalidateApproval])

  const setCouncilDraft = useCallback(value => updateCouncil('text', value), [updateCouncil])
  const setCouncilSpikeId = useCallback(value => updateCouncil('slug', value), [updateCouncil])

  const approveAnchor = useCallback((text, slug, itemId, version) => {
    if (!text?.trim() || !itemId || !Number.isInteger(version) || version < 1) {
      setApproval(null)
      return null
    }
    const record = { itemId, version, text, slug, approver: 'operator' }
    setApproval(record)
    return record
  }, [])

  const beginAnchor = useCallback((text = '', slug = 'post-1', origin = 'operator') => {
    const anchor = { itemId: newItemId(), version: 1, text, slug: slug || 'post-1', origin }
    anchorRef.current = anchor
    setDistributeAnchor(anchor)
    invalidateApproval()
    setActiveTab?.('distribute')
    return anchor
  }, [invalidateApproval, newItemId, setActiveTab])

  // Compatibility for callers that explicitly approve the unchanged incoming anchor.
  // New consumers use approveAnchor with their own current item/version snapshot.
  const setApprovedText = useCallback(text => {
    const anchor = anchorRef.current
    if (anchor && text === anchor.text) return approveAnchor(text, anchor.slug, anchor.itemId, anchor.version)
    invalidateApproval()
    return null
  }, [approveAnchor, invalidateApproval])

  const handleSendToCouncilWithDraft = useCallback((draftText, slug) => {
    const next = { itemId: newItemId(), version: 1, text: draftText, slug: slug || 'spike-1' }
    councilRef.current = next
    setCouncil(next)
    invalidateApproval()
    setActiveTab?.('council')
    return next
  }, [invalidateApproval, newItemId, setActiveTab])

  const handleSendToCouncil = useCallback((item) => {
    const slug = item.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)
    const snippetBlock = item.body_snippet ? `> ${item.body_snippet}\n\n` : ''
    return handleSendToCouncilWithDraft(`# ${item.title}\n\n${item.url ? `Source: ${item.url}\n\n` : ''}${snippetBlock}Draft content goes here...`, slug)
  }, [handleSendToCouncilWithDraft])

  const handleSendToDistribute = useCallback((text, slug) => beginAnchor(text, slug || 'published-post'), [beginAnchor])

  const handleApprove = useCallback((text, slug) => {
    if (!text?.trim()) return null
    const anchor = beginAnchor(text, slug || 'published-post')
    return approveAnchor(anchor.text, anchor.slug, anchor.itemId, anchor.version)
  }, [approveAnchor, beginAnchor])

  return {
    approval,
    approveAnchor,
    invalidateApproval,
    beginAnchor,
    distributeAnchor,
    councilIdentity: council,
    approvedText: approval?.text || '',
    setApprovedText,
    handleApprove,
    councilDraft: council.text,
    setCouncilDraft,
    councilSpikeId: council.slug,
    setCouncilSpikeId,
    distributeText: distributeAnchor?.text || '',
    distributeSlug: distributeAnchor?.slug || 'post-1',
    handleSendToCouncil,
    handleSendToCouncilWithDraft,
    handleSendToDistribute,
  }
}

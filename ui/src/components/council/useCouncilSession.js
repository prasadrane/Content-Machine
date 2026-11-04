import { useEffect, useRef, useState } from 'react'
import { getCouncilHistory, getCouncilSpikes, runCouncil } from '../../api/council'
import { runHumanize } from '../../api/humanize'

// Session-only ownership. Backend history has slugs but no immutable version IDs.
export function useCouncilSession({ draft, spikeId, setDraft, setSpikeId, onApprove, councilIdentity }) {
  const current = useRef({ text: draft, slug: spikeId, version: councilIdentity?.version ?? 0, itemId: councilIdentity?.itemId ?? null })
  if (councilIdentity) {
    current.current = { text: draft, slug: spikeId, version: councilIdentity.version, itemId: councilIdentity.itemId }
  } else if (current.current.text !== draft || current.current.slug !== spikeId) {
    current.current = { text: draft, slug: spikeId, version: current.current.version + 1 }
  }
  const sequence = useRef(0)
  const historySequence = useRef(0)
  const mounted = useRef(true)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [historyData, setHistoryData] = useState(null)
  const [recentSpikes, setRecentSpikes] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const [humanizing, setHumanizing] = useState(false)
  const [humanizedResult, setHumanizedResult] = useState(null)
  const [humanizeError, setHumanizeError] = useState('')
  const [maxIterations, setMaxIterations] = useState(1)
  const [pendingApproval, setPendingApproval] = useState(null)

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  const snapshot = text => ({ ...current.current, text: text ?? current.current.text, requestId: ++sequence.current })
  const isEarlier = input => Boolean(input && (input.itemId !== current.current.itemId || input.version !== current.current.version || input.slug !== spikeId || input.text !== current.current.text))
  const fetchHistory = async slug => {
    const requestId = ++historySequence.current
    const itemId = current.current.itemId
    if (!slug) return
    try {
      const data = await getCouncilHistory(slug)
      if (mounted.current && requestId === historySequence.current && current.current.slug === slug && current.current.itemId === itemId) setHistoryData(data)
    } catch { /* History is optional; never replace current draft on failure. */ }
  }
  const fetchSpikes = async () => {
    try {
      const data = await getCouncilSpikes()
      if (mounted.current) setRecentSpikes(data || [])
    } catch { /* Recent items are optional. */ }
  }
  useEffect(() => { fetchSpikes() }, [])
  useEffect(() => {
    setHistoryData(null)
    fetchHistory(spikeId)
  }, [spikeId, councilIdentity?.itemId])
  useEffect(() => { setPendingApproval(null) }, [draft, spikeId, councilIdentity?.itemId, councilIdentity?.version])

  const handleReview = async event => {
    event.preventDefault()
    if (!draft.trim()) { setError('Draft text cannot be empty.'); return }
    const input = snapshot()
    setLoading(true)
    setError('')
    // Keep the previous result available until the replacement succeeds.
    try {
      const data = await runCouncil({ draft: input.text, spike_id: input.slug || 'council-ui', max_iterations: maxIterations })
      if (!mounted.current) return
      setResult({ ...data, reviewInput: input })
      if (current.current.slug === input.slug && current.current.itemId === input.itemId) fetchHistory(input.slug)
      fetchSpikes()
    } catch (err) {
      if (mounted.current) setError(`Review for ${input.slug || 'this draft'} failed: ${err.message || 'Please try again.'}`)
    } finally {
      if (mounted.current) setLoading(false)
    }
  }
  const requestApproval = (text, meta = {}) => setPendingApproval({ ...meta, text, input: snapshot() })
  const confirmApproval = () => {
    if (!pendingApproval || isEarlier(pendingApproval.input)) return
    const { text, input } = pendingApproval
    setPendingApproval(null)
    onApprove?.(text, input.slug)
  }
  const best = historyData?.best
  const handleHumanize = async sourceText => {
    const text = sourceText || best?.draft || draft
    if (!text?.trim()) { setHumanizeError('No draft text available to polish.'); return }
    const input = snapshot(text)
    setHumanizing(true)
    setHumanizeError('')
    try {
      const data = await runHumanize({ text, channel: 'linkedin_post', tone: 'pragmatic_architect' })
      if (mounted.current) setHumanizedResult({ ...data, reviewInput: input })
    } catch (err) {
      if (mounted.current) setHumanizeError(`Polish for ${input.slug || 'this draft'} failed: ${err.message || 'Please try again.'}`)
    } finally {
      if (mounted.current) setHumanizing(false)
    }
  }
  return {
    loading, result, error, historyData, recentSpikes, showHistory, setShowHistory,
    humanizing, humanizedResult, setHumanizedResult, humanizeError, maxIterations, setMaxIterations,
    pendingApproval, setPendingApproval, requestApproval, confirmApproval, best,
    handleReview, handleHumanize,
    handleSelectSpike: setSpikeId,
    handleLoadDraft: text => { if (text) setDraft(text) },
    resultIsEarlier: isEarlier(result?.reviewInput),
    polishIsEarlier: isEarlier(humanizedResult?.reviewInput),
  }
}

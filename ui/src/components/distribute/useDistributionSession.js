import { useEffect, useId, useRef, useState } from 'react'
import { runDistribute, getDistributeHistory } from '../../api/distribute'

export function useDistributionSession({ initialText = '', initialSlug = 'post-1', approvedText = '', approval, anchorIdentity, onApprove, onInvalidateApproval }) {
  const id = useId()
  const sequence = useRef(0)
  const initial = anchorIdentity || { itemId: id, version: 1, text: initialText, slug: initialSlug || 'post-1', origin: 'operator' }
  const [anchor, setAnchor] = useState(initial)
  const current = useRef(initial)
  const [localApproval, setLocalApproval] = useState(() => approval === undefined && approvedText && approvedText === initial.text ? { ...initial } : null)
  const [reviewed, setReviewed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [output, setOutput] = useState(null)
  const [historyItems, setHistoryItems] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [activeFormat, setActiveFormat] = useState('linkedin')
  const controlled = approval !== undefined
  const record = controlled ? approval : localApproval
  const isApproved = Boolean(anchor.text.trim() && record && record.itemId === anchor.itemId && record.version === anchor.version && record.text === anchor.text && record.slug === anchor.slug)
  const invalidate = () => { setLocalApproval(null); setReviewed(false); onInvalidateApproval?.() }
  const replace = next => { current.current = next; setAnchor(next) }
  const edit = (field, value) => {
    if (current.current[field] === value) return
    replace({ ...current.current, [field]: value, version: current.current.version + 1 })
    invalidate()
  }
  useEffect(() => {
    const next = anchorIdentity || { itemId: `${id}-${++sequence.current}`, version: 1, text: initialText, slug: initialSlug || 'post-1', origin: 'operator' }
    replace(next)
    setReviewed(false)
    if (!anchorIdentity) setLocalApproval(approval === undefined && approvedText === next.text && approvedText ? { ...next } : null)
  }, [anchorIdentity, initialText, initialSlug])
  const fetchHistory = async () => {
    setHistoryLoading(true)
    try { const data = await getDistributeHistory(); setHistoryItems(data?.items || []) }
    catch { /* History is optional; keep the working anchor. */ }
    finally { setHistoryLoading(false) }
  }
  useEffect(() => { fetchHistory() }, [])
  const firstFormat = data => ['linkedin', 'x_thread', 'video_script_short', 'video_script', 'video_script_long', 'newsletter'].find(key => data[key]) || 'linkedin'
  const selectHistory = item => {
    if (!item) return
    const next = { itemId: `${id}-history-${++sequence.current}`, version: 1, text: item.anchor_text || '', slug: item.slug || 'post-1', origin: item.bundle?.replayed ? 'replayed' : 'stored' }
    replace(next)
    invalidate()
    setOutput(item.has_bundle && item.bundle ? { anchor: next, data: item.bundle, origin: next.origin } : null)
    if (item.bundle) setActiveFormat(firstFormat(item.bundle))
  }
  const approveCurrent = () => {
    if (!reviewed || !anchor.text.trim()) return
    const next = onApprove?.(anchor.text, anchor.slug, anchor.itemId, anchor.version)
    if (!controlled) setLocalApproval(next || { ...anchor })
    setReviewed(false)
  }
  const generate = async (event, options) => {
    event.preventDefault()
    if (!isApproved) { setError('Approve this exact text before generating derivatives.'); return }
    const input = { ...current.current, requestId: ++sequence.current }
    setLoading(true)
    setError('')
    try {
      const data = await runDistribute({ anchor_post: input.text, project_slug: input.slug || 'post', ...options })
      setOutput({ anchor: input, data, origin: data.replayed ? 'replayed' : 'generated' })
      setActiveFormat(firstFormat(data))
      fetchHistory()
    } catch (err) { setError(`Generation for ${input.slug} failed: ${err.message || 'Please try again.'}`) }
    finally { setLoading(false) }
  }
  return {
    anchor, output, loading, error, reviewed, setReviewed, isApproved, approveCurrent,
    historyItems, historyLoading, activeFormat, setActiveFormat, selectHistory, generate,
    editText: value => edit('text', value), editSlug: value => edit('slug', value),
    isEarlier: Boolean(output && (output.anchor.itemId !== anchor.itemId || output.anchor.version !== anchor.version)),
  }
}

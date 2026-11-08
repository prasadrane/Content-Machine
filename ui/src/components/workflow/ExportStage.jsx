import { useEffect, useRef, useState } from 'react'
import { Copy, Download } from 'lucide-react'
import { getDownload } from '../../api/workflow'
import { formatLabel } from './workflowUtils'

export default function ExportStage({ flow }) {
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [target, setTarget] = useState('')
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])
  const approved = !flow.dirty && flow.approval &&
    flow.approval.approval_id === flow.item.active_approval_id
  const output = flow.exported
  const ready = approved && output?.version_id === flow.approval.version_id &&
    (!flow.approval.artifact_digest || output.artifact_digest === flow.approval.artifact_digest)

  async function copy(text) {
    setError('')
    setNotice('')
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(text)
      if (mounted.current) setNotice('Copied')
    } catch {
      if (mounted.current) setError('Could not copy. Select the text below and copy it manually.')
    }
  }
  async function download() {
    setBusy(true)
    setError('')
    setNotice('')
    let url
    let anchor
    try {
      const file = await getDownload(flow.item.item_id, flow.approval.version_id)
      if (!mounted.current) return
      if (file.artifactDigest !== flow.approval.artifact_digest) {
        throw new Error('The downloaded snapshot does not match this approval. Reload the approved version.')
      }
      url = URL.createObjectURL(file.blob)
      anchor = document.createElement('a')
      anchor.href = url
      anchor.download = file.filename
      document.body.append(anchor)
      anchor.click()
      setNotice('Download started')
    } catch (failure) {
      if (mounted.current) setError(`Could not start the download. ${failure.message}`)
    } finally {
      anchor?.remove()
      if (url) URL.revokeObjectURL(url)
      if (mounted.current) setBusy(false)
    }
  }
  if (!approved) return <p className="cm-status cm-status-info">Approve your saved version to export it.</p>
  if (!ready) return <div className="cm-panel space-y-4">
    <p>Load your approved version to copy or download it.</p>
    <button className="cm-button cm-button-primary" disabled={flow.busy} onClick={flow.loadExport}>Load approved version</button>
  </div>
  return <section className="cm-panel space-y-5">
    <h2 className="cm-panel-title">Ready to copy or download</h2>
    <p className="cm-muted">Approved version <span className="break-all">{output.version_id}</span>. Publish it yourself when you are ready.</p>
    {error && <p role="alert" className="cm-status cm-status-error">{error}</p>}
    {notice && <p role="status" className="cm-status cm-status-success">{notice}</p>}
    <div className="cm-page-actions">
      <button className="cm-button cm-button-primary" disabled={busy || flow.busy}
        onClick={() => copy(output.segments.join('\n\n'))}><Copy size={16} aria-hidden="true" />Copy</button>
      <button className="cm-button cm-button-secondary" disabled={busy || flow.busy}
        onClick={download}><Download size={16} aria-hidden="true" />Download</button>
    </div>
    {output.segments.map((text, index) => <div key={index} className="cm-subpanel space-y-3">
      {output.segments.length > 1 && <div className="flex items-center justify-between gap-2">
        <h3 className="cm-label mb-0">Post {index + 1}</h3>
        <button className="cm-button cm-button-quiet" onClick={() => copy(text)}>Copy post {index + 1}</button>
      </div>}
      <pre className="cm-prose whitespace-pre-wrap">{text}</pre>
    </div>)}
    {flow.pairs.length > 0 && <details className="cm-divider space-y-3">
      <summary className="cursor-pointer font-medium">Adapt for another platform</summary>
      <p className="cm-muted">Start a linked draft from this approved source. Review and approve the new draft separately.</p>
      <label className="cm-label">Adapt for
        <select className="cm-select mt-2" value={target} onChange={event => setTarget(event.target.value)}>
          <option value="">Choose a format</option>
          {flow.pairs.map(pair => <option key={pair.format} value={pair.format}>{formatLabel(pair)}</option>)}
        </select>
      </label>
      <button className="cm-button cm-button-secondary" disabled={!target || busy || flow.busy}
        onClick={() => flow.adapt(flow.pairs.find(pair => pair.format === target))}>Create linked draft</button>
    </details>}
  </section>
}

import { useRef, useState } from 'react'
import WorkflowTextField from './WorkflowTextField'

export default function ArtifactEditor({ flow, isActive }) {
  const thread = flow.item.format === 'x_thread'
  const segments = flow.draft.artifact.segments.length ? flow.draft.artifact.segments : ['']
  const [keys, setKeys] = useState(() => segments.map((_, index) => index))
  const nextKey = useRef(segments.length)
  const change = index => value => flow.updateDraft(previous => {
    const next = previous.artifact.segments.length ? [...previous.artifact.segments] : ['']
    next[index] = typeof value === 'function' ? value(next[index]) : value
    return { ...previous, artifact: { ...previous.artifact, segments: next } }
  })
  return <div className="space-y-5">
    {segments.map((text, index) => <div key={keys[index]} className="space-y-2">
      <WorkflowTextField label={thread ? `Post ${index + 1}` : 'Draft text'} value={text}
        onChange={change(index)} enabled={isActive && !flow.busy} rows={thread ? 5 : 12} />
      {thread && <div className="flex items-center justify-between gap-2">
        <span className="cm-muted">{Array.from(text).length} / 280 characters</span>
        {segments.length > 1 && <button className="cm-button cm-button-quiet" disabled={flow.busy}
          onClick={() => {
            setKeys(previous => previous.filter((_, position) => position !== index))
            flow.updateDraft(previous => ({ ...previous,
              artifact: { segments: previous.artifact.segments.filter((_, position) => position !== index) },
            }))
          }} aria-label={`Remove post ${index + 1}`}>Remove post</button>}
      </div>}
    </div>)}
    {thread && <button className="cm-button cm-button-secondary" disabled={flow.busy || segments.length >= 500}
      onClick={() => {
        const key = nextKey.current++
        setKeys(previous => [...previous, key])
        flow.updateDraft(previous => ({ ...previous, artifact: { segments: [...segments, ''] } }))
      }}>Add post</button>}
  </div>
}

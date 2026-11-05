import { useEffect, useState } from 'react'
import { getCouncilHistory } from '../api/council'
import { getDistributeHistory } from '../api/distribute'
import { DISTRIBUTION_FORMATS } from '../lib/constants'

const SAMPLE_ID = 'demo-cache-stampede'
const panel = 'cm-panel space-y-3'
const prose = 'cm-prose whitespace-pre-wrap break-words'

export default function SampleStory({ onClose }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let alive = true
    Promise.all([getCouncilHistory(SAMPLE_ID), getDistributeHistory()])
      .then(([review, history]) => {
        if (alive) setData({ review: review?.best, item: history?.items?.find(item => item.slug === SAMPLE_ID && item.bundle) })
      })
      .catch(err => { if (alive) setError(err.message || 'Could not load the stored example.') })
    return () => { alive = false }
  }, [])
  const item = data?.item
  const formats = DISTRIBUTION_FORMATS.filter(format => item?.bundle?.[format.id] || (format.id === 'video_script_short' && item?.bundle?.video_script))
  return (
    <section aria-labelledby="sample-story-title" className="cm-page">
      <div className="cm-page-header">
        <div>
          <h2 id="sample-story-title" className="cm-page-title">A completed editorial example</h2>
          <p className="cm-page-description max-w-3xl">Read-only sample. Sources, first-person experience and Council reviews in this cache-stampede example are synthetic. They do not describe the owner's lived experience or prove live model quality.</p>
        </div>
        <button type="button" onClick={onClose} className="cm-button cm-button-secondary">Return to workspace</button>
      </div>
      {!data && !error && <p role="status">Loading the stored example...</p>}
      {error && <p role="alert" className="cm-status cm-status-error">{error}</p>}
      {data && <>
        <section className={panel} aria-labelledby="sample-source">
          <h3 id="sample-source" className="cm-panel-title">1. Source and author perspective</h3>
          <p className="cm-prose">The synthetic demo source is demo.example.com. First-person statements in the sample draft are illustrative author perspective, not verified facts or your experience.</p>
        </section>
        <section className={panel} aria-labelledby="sample-review">
          <h3 id="sample-review" className="cm-panel-title">2. Stored editorial review</h3>
          <p className="cm-prose">Synthetic editorial review, not fact verification. {typeof data.review?.score === 'number' ? `Sample score: ${data.review.score.toFixed(1)} / 10.` : ''}</p>
          {data.review?.draft ? <p className={prose}>{data.review.draft}</p> : <p role="status">The sample review is unavailable on this server.</p>}
        </section>
        <section className={panel} aria-labelledby="sample-approval">
          <h3 id="sample-approval" className="cm-panel-title">3. Your approval is a separate decision</h3>
          <p className="cm-prose">Illustrative approval step; not approved by you. No recorded human approval identity is available for this seed. In your workspace, you explicitly approve the exact text before creating formats.</p>
        </section>
        <section className={panel} aria-labelledby="sample-anchor">
          <h3 id="sample-anchor" className="cm-panel-title">4. Stored distribution anchor</h3>
          <p className="cm-prose">This is the stored anchor associated with the sample bundle, not the exact Council draft shown above. These stored formats are illustrative and were not generated from your text.</p>
          {item?.anchor_text ? <p className={prose}>{item.anchor_text}</p> : <p role="status">The original sample anchor is unavailable.</p>}
        </section>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {formats.map(format => <section key={format.id} className={panel} aria-label={`Stored sample ${format.shortLabel}`}>
            <h3 className="cm-panel-title">{format.shortLabel}</h3>
            <p className="cm-muted">Stored illustrative sample output</p>
            <p className={prose}>{item.bundle[format.id] || item.bundle.video_script}</p>
          </section>)}
        </div>
        {formats.length < 2 && <p role="status" className="cm-prose">Fewer than two stored formats are available on this server; this example is incomplete.</p>}
      </>}
    </section>
  )
}

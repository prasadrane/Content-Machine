import ArtifactEditor from './ArtifactEditor'
import ReviewStatus from './ReviewStatus'
import AIWorkflowPanel from './AIWorkflowPanel'
import IdeaContextFields from './IdeaContextFields'

export default function DraftStage({ flow, isActive }) {
  return <section className="cm-panel space-y-5">
    <h2 className="cm-panel-title">Make the idea your own</h2>
    <p className="cm-muted">Write or paste your draft. Keep technical claims grounded in your notes and sources.</p>
    <ArtifactEditor flow={flow} isActive={isActive} />
    <details className="cm-subpanel space-y-4">
      <summary className="cursor-pointer font-medium">Idea and source context</summary>
      <IdeaContextFields flow={flow} isActive={isActive} />
    </details>
    <ReviewStatus flow={flow} />
    <AIWorkflowPanel flow={flow} />
    <div className="cm-page-actions">
      <button className="cm-button cm-button-secondary" disabled={flow.busy || !flow.dirty} onClick={flow.save}>Save draft</button>
      <button className="cm-button cm-button-primary" disabled={flow.busy || !flow.draft.artifact.segments.some(text => text.trim())}
        onClick={flow.skip}>Skip AI review and continue</button>
    </div>
  </section>
}

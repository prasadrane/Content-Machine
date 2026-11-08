import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, Clock, Save } from 'lucide-react'
import PlatformIcon from '../ui/PlatformIcon'
import { useWorkflow } from './useWorkflow'
import { formatLabel } from './workflowUtils'
import ContentList, { STAGES } from './ContentList'
import NewContent from './NewContent'
import IdeaStage from './IdeaStage'
import DraftStage from './DraftStage'
import ApproveStage from './ApproveStage'
import ExportStage from './ExportStage'
import HistoryPanel from './HistoryPanel'
import { VoiceRecoveryPanel, VoiceRecoveryProvider } from './VoiceRecovery'
import { canVisitStage, useWorkflowRoute } from './useWorkflowRoute'

export default function WorkflowTab({ isActive = true, onOpenSettings, route, navigateRoute }) {
  const flow = useWorkflow()
  useWorkflowRoute(flow, route, navigateRoute, isActive)
  const [confirmDiscard, setConfirmDiscard] = useState(false)
  const stageHeading = useRef(null)
  const historyButton = useRef(null)
  useEffect(() => { if (!flow.dirty) setConfirmDiscard(false) }, [flow.dirty])
  useEffect(() => { stageHeading.current?.focus({ preventScroll: true }) }, [flow.stage, flow.screen])
  useEffect(() => {
    if (!flow.dirty) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [flow.dirty])
  return <VoiceRecoveryProvider identity={{
    ownerId: flow.principal?.owner_id || flow.item?.owner_id,
    itemId: flow.item?.item_id,
    revision: flow.item?.working_revision,
  }}><div className="cm-page">
    <VoiceRecoveryPanel />
    {flow.error && <div role="alert" className="cm-status cm-status-error space-y-2">
      <p>{flow.error}</p>
      {flow.screen === 'list' && <button className="cm-button cm-button-secondary" disabled={flow.loading}
        onClick={flow.refresh}>Try again</button>}
      {flow.conflict && <p>Your text is preserved. Copy your changes before reloading a version edited elsewhere.</p>}
    </div>}
    {flow.capabilitiesError && <div className="cm-status cm-status-warning">
      <p>{flow.capabilitiesError}</p>
      <button className="cm-button cm-button-quiet" onClick={flow.refresh}>Retry destinations</button>
    </div>}
    {flow.notice && <p role="status" className="cm-status cm-status-success">{flow.notice}</p>}
    {flow.screen === 'list' && <ContentList flow={flow} />}
    <div hidden={flow.screen !== 'new'}>
      <NewContent key={flow.item?.item_id || 'new'} flow={flow} />
    </div>
    {flow.screen === 'item' && flow.item && flow.draft && <>
      <header className="cm-page-header">
        <div className="space-y-3 min-w-0">
          <button className="cm-button cm-button-quiet" disabled={flow.dirty || flow.busy} onClick={flow.showList}>
            <ArrowLeft size={16} aria-hidden="true" />Saved work</button>
          <h1 className="cm-page-title break-words">{flow.item.title}</h1>
          <p className="cm-muted flex items-center gap-2"><PlatformIcon platform={flow.item.destination} />{formatLabel(flow.item)}</p>
        </div>
        <div className="cm-page-actions">
          <span role="status" className="cm-muted">{flow.busy ? 'Saving or loading…' : flow.dirty ? 'Unsaved changes' : `Saved · Revision ${flow.item.working_revision}`}</span>
          <button className="cm-button cm-button-secondary" disabled={flow.busy || !flow.dirty} onClick={flow.save}>
            <Save size={16} aria-hidden="true" />Save</button>
          {flow.dirty && <button className="cm-button cm-button-quiet" disabled={flow.busy}
            onClick={() => setConfirmDiscard(true)}>Discard changes</button>}
          <button ref={historyButton} className="cm-button cm-button-quiet" disabled={flow.busy} onClick={flow.loadHistory}>
            <Clock size={16} aria-hidden="true" />History</button>
        </div>
      </header>
      {flow.dirty && confirmDiscard && <div className="cm-status cm-status-warning space-y-3" role="group" aria-label="Discard changes">
        <p>Discard your unsaved changes and return to the saved version?</p>
        <div className="cm-page-actions">
          <button className="cm-button cm-button-secondary" disabled={flow.busy}
            onClick={() => { flow.discard(); setConfirmDiscard(false) }}>Discard unsaved changes</button>
          <button className="cm-button cm-button-quiet" onClick={() => setConfirmDiscard(false)}>Keep editing</button>
        </div>
      </div>}
      <nav aria-label="Content workflow" className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {STAGES.map(([id, label], index) => <button key={id}
          className={`cm-chip ${flow.stage === id ? 'cm-chip-active' : ''}`}
          aria-current={flow.stage === id ? 'step' : undefined} disabled={!canVisitStage(flow, id)}
          onClick={() => flow.setStage(id)}>{index + 1}. {label}</button>)}
      </nav>
      <h2 ref={stageHeading} tabIndex={-1} className="sr-only">{STAGES.find(([id]) => id === flow.stage)?.[1]}</h2>
      {flow.stage === 'idea' && <IdeaStage flow={flow} isActive={isActive} onManageSources={onOpenSettings} />}
      {flow.stage === 'draft_review' && <DraftStage flow={flow} isActive={isActive} />}
      {flow.stage === 'approve' && <ApproveStage flow={flow} />}
      {flow.stage === 'export' && <ExportStage key={flow.approval?.version_id} flow={flow} />}
      {flow.history && <HistoryPanel key={flow.item.item_id} itemId={flow.item.item_id}
        currentArtifact={flow.draft.artifact} history={flow.history} busy={flow.busy} dirty={flow.dirty}
        onRestore={async id => {
          const before = flow.item.working_revision
          await flow.restore(id)
          if (flow.itemRef.current.working_revision !== before) stageHeading.current?.focus()
        }} onClose={() => { flow.closeHistory(); historyButton.current?.focus() }} />}
    </>}
  </div></VoiceRecoveryProvider>
}

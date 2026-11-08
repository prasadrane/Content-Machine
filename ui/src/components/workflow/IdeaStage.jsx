import { useState } from 'react'
import { Lightbulb, Search } from 'lucide-react'
import IdeaContextFields from './IdeaContextFields'
import DiscoveryPane from './DiscoveryPane'

export default function IdeaStage({ flow, isActive, onManageSources }) {
  const [source, setSource] = useState('own')
  return <section className="cm-panel space-y-5">
    <h2 className="cm-panel-title">What do you want to share?</h2>
    <div className="grid sm:grid-cols-2 gap-3">
      <button className={`cm-button ${source === 'own' ? 'cm-button-primary' : 'cm-button-secondary'}`}
        aria-pressed={source === 'own'} onClick={() => setSource('own')}>
        <Lightbulb size={18} aria-hidden="true" />Your idea</button>
      <button className={`cm-button ${source === 'discover' ? 'cm-button-primary' : 'cm-button-secondary'}`}
        aria-pressed={source === 'discover'} onClick={() => setSource('discover')}>
        <Search size={18} aria-hidden="true" />Discover ideas</button>
    </div>
    {source === 'discover' && <DiscoveryPane key={flow.item.item_id}
      attachedSources={flow.draft.context.sources || []} disabled={flow.busy}
      onManageSources={onManageSources}
      onUse={entry => flow.updateDraft(previous => {
        const sources = previous.context.sources || []
        if (sources.length >= 200 || sources.some(source => source.source_id === entry.source_id && source.url === entry.url)) return previous
        return { ...previous, context: { ...previous.context, sources: [...sources, entry] } }
      })} />}
    <IdeaContextFields flow={flow} isActive={isActive} />
    <p className="cm-muted">Have a draft already? Continue to the editor and paste it there.</p>
    <button className="cm-button cm-button-primary" disabled={flow.busy} onClick={flow.continueToDraft}>
      Continue to draft
    </button>
  </section>
}

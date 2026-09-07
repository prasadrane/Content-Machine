import { useState } from 'react'

export function useSharedFlow(setActiveTab) {
  const [councilDraft, setCouncilDraft] = useState('')
  const [councilSpikeId, setCouncilSpikeId] = useState('spike-1')
  const [distributeText, setDistributeText] = useState('')
  const [distributeSlug, setDistributeSlug] = useState('post-1')

  const handleSendToCouncil = (item) => {
    setCouncilSpikeId(item.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30))
    const snippetBlock = item.body_snippet ? `> ${item.body_snippet}\n\n` : ''
    setCouncilDraft(`# ${item.title}\n\n${item.url ? `Source: ${item.url}\n\n` : ''}${snippetBlock}Draft content goes here...`)
    if (setActiveTab) setActiveTab('council')
  }

  const handleSendToCouncilWithDraft = (draftText, slug) => {
    setCouncilSpikeId(slug || 'spike-1')
    setCouncilDraft(draftText)
    if (setActiveTab) setActiveTab('council')
  }

  const handleSendToDistribute = (text, slug) => {
    setDistributeText(text)
    setDistributeSlug(slug || 'published-post')
    if (setActiveTab) setActiveTab('distribute')
  }

  return {
    councilDraft,
    setCouncilDraft,
    councilSpikeId,
    setCouncilSpikeId,
    distributeText,
    distributeSlug,
    handleSendToCouncil,
    handleSendToCouncilWithDraft,
    handleSendToDistribute,
  }
}

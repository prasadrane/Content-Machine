import React, { useState, useEffect } from 'react'
import { getLessons, addCustomLesson, diffLessons, approveLesson, rejectLesson } from '../../api/lessons'
import CustomRuleCard from './CustomRuleCard'
import DiffExtractor from './DiffExtractor'
import RulesLists from './RulesLists'

export default function LessonsTab() {
  const [activeRules, setActiveRules] = useState([])
  const [pendingRules, setPendingRules] = useState([])
  const [draftText, setDraftText] = useState('')
  const [pubText, setPubText] = useState('')
  const [proposals, setProposals] = useState([])
  const [loadingDiff, setLoadingDiff] = useState(false)
  const [error, setError] = useState('')
  const [customRuleText, setCustomRuleText] = useState('')
  const [loadingCustom, setLoadingCustom] = useState(false)
  const [customSuccess, setCustomSuccess] = useState('')

  const fetchLessons = async () => {
    try {
      const data = await getLessons()
      setActiveRules(data.rules || data.active || [])
      setPendingRules(data.pending || [])
    } catch {}
  }

  const handleAddCustomRule = async (e) => {
    e.preventDefault()
    if (!customRuleText.trim()) return
    setLoadingCustom(true)
    setError('')
    setCustomSuccess('')

    try {
      await addCustomLesson({
        rule_text: customRuleText.trim(),
        provenance_project: 'manual',
        auto_approve: true,
      })
      setCustomRuleText('')
      setCustomSuccess('Rule active in Council loop!')
      setTimeout(() => setCustomSuccess(''), 3500)
      fetchLessons()
    } catch (err) {
      setError(err.message || 'Failed to add custom rule')
    } finally {
      setLoadingCustom(false)
    }
  }

  useEffect(() => {
    fetchLessons()
  }, [])

  const handleDiff = async (e) => {
    e.preventDefault()
    if (!draftText.trim() || !pubText.trim()) {
      setError('Both draft and published texts are required.')
      return
    }
    setLoadingDiff(true)
    setError('')
    setProposals([])

    try {
      const data = await diffLessons({ draft: draftText, published: pubText, project_id: 'ui-diff' })
      setProposals(data.rules || [])
    } catch (err) {
      setError(err.message || 'Diff extraction failed.')
    } finally {
      setLoadingDiff(false)
    }
  }

  const handleApprove = async (ruleId) => {
    try {
      await approveLesson(ruleId)
      fetchLessons()
      setProposals(prev => prev.filter(p => p.rule_id !== ruleId))
    } catch {}
  }

  const handleReject = async (ruleId) => {
    try {
      await rejectLesson(ruleId)
      fetchLessons()
      setProposals(prev => prev.filter(p => p.rule_id !== ruleId))
    } catch {}
  }

  return (
    <div className="space-y-8 animate-fadeIn">
      <div className="border-b border-[#e3dacc] pb-5">
        <h2 className="font-serif text-2xl font-medium tracking-tight text-[#141413]">Editorial Lessons</h2>
        <p className="text-sm text-[#87867f] mt-1 font-sans">
          Codified writing rules and approved stylistic constraints.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        {/* Left Column: Direct Add + Diff Extractor */}
        <div className="space-y-6">
          <CustomRuleCard
            customRuleText={customRuleText}
            onTextChange={setCustomRuleText}
            loadingCustom={loadingCustom}
            customSuccess={customSuccess}
            onAdd={handleAddCustomRule}
          />
          <DiffExtractor
            draftText={draftText}
            pubText={pubText}
            onDraftChange={setDraftText}
            onPubChange={setPubText}
            loadingDiff={loadingDiff}
            error={error}
            onDiff={handleDiff}
            proposals={proposals}
            onApproveProposal={handleApprove}
            onRejectProposal={handleReject}
          />
        </div>

        {/* Right Column: Pending Review Queue + Active Rules List */}
        <RulesLists
          pendingRules={pendingRules}
          activeRules={activeRules}
          onApprove={handleApprove}
          onReject={handleReject}
          onRefresh={fetchLessons}
        />
      </div>
    </div>
  )
}

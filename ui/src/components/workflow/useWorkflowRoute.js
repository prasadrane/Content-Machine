import { useEffect, useRef, useState } from 'react'
import { routeHash } from '../../app/useWorkspaceNavigation'

export function canVisitStage(flow, stage) {
  if (flow.busy) return false
  const approved = !flow.dirty && Boolean(flow.approval) &&
    flow.approval.approval_id === flow.item?.active_approval_id
  const reviewed = flow.reviewIsCurrent || (flow.review?.state === 'skipped' &&
    flow.reviewBinding?.verified && flow.reviewBinding.itemId === flow.item?.item_id &&
    flow.reviewBinding.revision === flow.item?.working_revision && !flow.dirty)
  if (stage === 'export') return approved
  if (stage === 'approve') return reviewed || approved
  return true
}

const viewRoute = flow => flow.screen === 'item' && flow.item
  ? { tab: 'workflow', screen: 'item', itemId: flow.item.item_id, stage: flow.stage }
  : { tab: 'workflow', screen: flow.screen }

export function useWorkflowRoute(flow, route, navigateRoute, isActive) {
  const latest = useRef(flow)
  latest.current = flow
  const handled = useRef(null)
  const target = useRef(null)
  const loading = useRef(false)
  const mounted = useRef(true)
  const [settled, setSettled] = useState(0)
  const requested = route?.tab === 'workflow' ? routeHash(route) : null
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])

  useEffect(() => {
    if (!isActive || !requested || handled.current === requested) return
    handled.current = requested
    const current = latest.current
    const differentItem = route.screen !== 'item' || route.itemId !== current.item?.item_id
    if ((differentItem && current.dirty) || current.busy) {
      current.setNotice(current.busy ? 'Wait for the current request before changing drafts.'
        : 'Save or discard your changes before leaving this draft. Your text is preserved.')
      const retained = viewRoute(current)
      handled.current = routeHash(retained)
      navigateRoute(retained, { replace: true })
      return
    }
    target.current = route
    if (route.screen === 'item' && differentItem) {
      loading.current = true
      current.open(route.itemId).finally(() => {
        loading.current = false
        if (mounted.current) setSettled(value => value + 1)
      })
    } else setSettled(value => value + 1)
  }, [requested, isActive, navigateRoute])

  useEffect(() => {
    if (!route || !isActive || route.tab !== 'workflow' || loading.current || flow.busy) return
    const incoming = target.current
    if (incoming) {
      target.current = null
      if (incoming.screen === 'item' && flow.item?.item_id === incoming.itemId) {
        const allowed = canVisitStage(flow, incoming.stage)
        const stage = allowed ? incoming.stage : (flow.item.artifact.segments.length ? 'draft_review' : 'idea')
        flow.setStage(stage)
        if (!allowed) {
          flow.setNotice(incoming.stage === 'export' ? 'Approve this saved version before exporting.'
            : 'Review this draft or explicitly skip AI review before approval.')
          const next = { ...incoming, stage }
          handled.current = routeHash(next)
          navigateRoute(next, { replace: true })
        }
      } else if (incoming.screen === 'new') flow.setScreen('new')
      else if (incoming.screen === 'list') {
        if (flow.screen === 'new') flow.setScreen('list')
        else if (flow.screen !== 'list') flow.showList()
      } else {
        const retained = viewRoute(flow)
        handled.current = routeHash(retained)
        navigateRoute(retained, { replace: true })
      }
      return
    }
    const next = viewRoute(flow)
    const hash = routeHash(next)
    if (hash !== requested) {
      handled.current = hash
      navigateRoute(next)
    }
  }, [flow.screen, flow.item?.item_id, flow.stage, flow.busy, requested, isActive, navigateRoute, settled])
}

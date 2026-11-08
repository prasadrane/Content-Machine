import { useCallback, useEffect, useRef, useState } from 'react'

const stages = new Set(['idea', 'draft_review', 'approve', 'export'])
export function readWorkspaceRoute() {
  const hash = window.location.hash
  if (hash === '#/settings' || hash === '#/lessons') return { tab: hash.slice(2) }
  if (hash === '#/workflow/new') return { tab: 'workflow', screen: 'new' }
  const match = /^#\/workflow\/items\/([^/]+)\/([^/]+)$/.exec(hash)
  if (match && stages.has(match[2])) {
    try {
      const itemId = decodeURIComponent(match[1])
      if (itemId && itemId.length <= 200 && !/[\x00-\x20]/.test(itemId)) {
        return { tab: 'workflow', screen: 'item', itemId, stage: match[2] }
      }
    } catch { /* Malformed links fall back to saved work. */ }
  }
  return { tab: 'workflow', screen: 'list' }
}

export function routeHash(route) {
  if (route.tab !== 'workflow') return `#/${route.tab}`
  if (route.screen === 'item') return `#/workflow/items/${encodeURIComponent(route.itemId)}/${route.stage}`
  return route.screen === 'new' ? '#/workflow/new' : '#/workflow'
}

export function useWorkspaceNavigation() {
  const [route, setRoute] = useState(readWorkspaceRoute)
  const lastWorkflow = useRef(route.tab === 'workflow' ? route : { tab: 'workflow', screen: 'list' })
  if (route.tab === 'workflow') lastWorkflow.current = route
  useEffect(() => {
    const changed = () => setRoute(previous => {
      const next = readWorkspaceRoute()
      return routeHash(previous) === routeHash(next) ? previous : next
    })
    window.addEventListener('popstate', changed)
    window.addEventListener('hashchange', changed)
    return () => {
      window.removeEventListener('popstate', changed)
      window.removeEventListener('hashchange', changed)
    }
  }, [])
  const navigateRoute = useCallback((next, { replace = false } = {}) => {
    const hash = routeHash(next)
    if (window.location.hash !== hash) {
      window.history[replace ? 'replaceState' : 'pushState'](null, '', hash)
    }
    setRoute(previous => routeHash(previous) === hash ? previous : next)
  }, [])
  const navigate = useCallback(tab => navigateRoute(tab === 'workflow' ? lastWorkflow.current : { tab }), [navigateRoute])
  return { route, navigate, navigateRoute }
}

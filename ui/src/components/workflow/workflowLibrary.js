import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '../../api/workflow'

export function useWorkflowLibrary(setError) {
  const [items, setItems] = useState(null)
  const [pairs, setPairs] = useState([])
  const [principal, setPrincipal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(true)
  const [capabilitiesError, setCapabilitiesError] = useState('')
  const generation = useRef(0)

  const refresh = useCallback(async () => {
    const current = ++generation.current
    const isCurrent = () => current === generation.current
    setLoading(true)
    setCapabilitiesLoading(true)
    setError('')
    setCapabilitiesError('')
    const savedWork = api.getItems().then(content => {
      if (isCurrent()) setItems(content.items)
    }).catch(error => {
      if (isCurrent()) setError(error.message || 'Could not load your saved content.')
    }).finally(() => {
      if (isCurrent()) setLoading(false)
    })
    const capabilities = api.getCapabilities().then(content => {
      if (isCurrent()) {
        setPrincipal(content.principal || null)
        setPairs(content.pairs.filter(pair => pair.can_edit))
      }
    }).catch(error => {
      if (isCurrent()) setCapabilitiesError(error.message || 'Could not load destinations and formats.')
    }).finally(() => {
      if (isCurrent()) setCapabilitiesLoading(false)
    })
    await Promise.all([savedWork, capabilities])
  }, [setError])

  useEffect(() => {
    refresh()
    // A committed guest copy changes the saved library, not the selected item
    // or its unsaved editor state. Never remount the workspace to reveal it.
    const copied = () => { refresh() }
    window.addEventListener('cm:guest-work-copied', copied)
    return () => {
      generation.current += 1
      window.removeEventListener('cm:guest-work-copied', copied)
    }
  }, [refresh])

  return { items, pairs, principal, loading, capabilitiesLoading, capabilitiesError, refresh }
}

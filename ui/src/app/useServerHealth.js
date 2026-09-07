import { useEffect, useState } from 'react'
import { getHealth } from '../api/health'

export function useServerHealth(intervalMs = 10000) {
  const [serverOnline, setServerOnline] = useState(false)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await getHealth()
        setServerOnline(data.status === 'ok')
      } catch {
        setServerOnline(false)
      }
    }
    checkHealth()
    const timer = setInterval(checkHealth, intervalMs)
    return () => clearInterval(timer)
  }, [intervalMs])

  return serverOnline
}

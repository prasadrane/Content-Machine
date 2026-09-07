import { useState } from 'react'

export function useCopyToClipboard(resetMs = 2000) {
  const [copied, setCopied] = useState(false)

  const copy = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), resetMs)
      return true
    } catch {
      return false
    }
  }

  return { copied, copy, setCopied }
}

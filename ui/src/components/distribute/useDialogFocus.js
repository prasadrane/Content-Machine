import { useEffect, useRef } from 'react'

export function useDialogFocus(show, onClose) {
  const dialogRef = useRef(null)
  const closeRef = useRef(onClose)
  closeRef.current = onClose
  useEffect(() => {
    if (!show) return
    const opener = document.activeElement
    const dialog = dialogRef.current
    const selector = 'button:not([disabled]), input:not([disabled]), select, textarea, [tabindex="0"]'
    dialog?.querySelector(selector)?.focus()
    const keydown = event => {
      if (event.key === 'Escape') { event.preventDefault(); closeRef.current?.(); return }
      if (event.key !== 'Tab') return
      const controls = [...dialog.querySelectorAll(selector)]
      const first = controls[0]
      const last = controls[controls.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    dialog?.addEventListener('keydown', keydown)
    return () => { dialog?.removeEventListener('keydown', keydown); if (opener?.isConnected && !opener.closest('[hidden]')) opener.focus() }
  }, [show])
  return dialogRef
}

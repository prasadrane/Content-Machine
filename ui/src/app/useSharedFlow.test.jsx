import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useSharedFlow } from './useSharedFlow'

describe('shared editorial identity and approval', () => {
  it('hands off explicitly approved text with one exact anchor identity', () => {
    const navigate = vi.fn()
    const { result } = renderHook(() => useSharedFlow(navigate))
    act(() => result.current.handleApprove('A reviewed post', 'cache'))
    expect(result.current.approval).toMatchObject({
      itemId: result.current.distributeAnchor.itemId,
      version: result.current.distributeAnchor.version,
      text: 'A reviewed post', slug: 'cache', approver: 'operator',
    })
    expect(result.current.distributeText).toBe('A reviewed post')
    expect(navigate).toHaveBeenLastCalledWith('distribute')
  })

  it('does not borrow approval when a new anchor has matching text', () => {
    const { result } = renderHook(() => useSharedFlow())
    act(() => result.current.handleApprove('Same words', 'first'))
    const previous = result.current.approval
    act(() => result.current.beginAnchor('Same words', 'second'))
    expect(result.current.approval).toBeNull()
    expect(result.current.distributeAnchor.itemId).not.toBe(previous.itemId)
  })

  it('invalidates approval on whitespace edits and does not restore it after undo', () => {
    const { result } = renderHook(() => useSharedFlow())
    act(() => result.current.handleSendToCouncilWithDraft('Draft', 'item'))
    act(() => result.current.handleApprove('Draft', 'item'))
    act(() => result.current.setCouncilDraft('Draft '))
    expect(result.current.approval).toBeNull()
    act(() => result.current.setCouncilDraft('Draft'))
    expect(result.current.approval).toBeNull()
  })

  it('invalidates approval on changing the Council item even with identical text', () => {
    const { result } = renderHook(() => useSharedFlow())
    act(() => result.current.handleApprove('Draft', 'first'))
    act(() => result.current.setCouncilSpikeId('second'))
    expect(result.current.approval).toBeNull()
  })

  it('records explicit distribution approval using the submitted local version', () => {
    const { result } = renderHook(() => useSharedFlow())
    let record
    act(() => { record = result.current.approveAnchor('Exact text\n', 'entry', 'local-item', 4) })
    expect(record).toEqual(result.current.approval)
    expect(record).toMatchObject({ itemId: 'local-item', version: 4, text: 'Exact text\n' })
    act(() => result.current.invalidateApproval())
    expect(result.current.approval).toBeNull()
  })

  it('cannot approve blank text or an unspecified item/version', () => {
    const { result } = renderHook(() => useSharedFlow())
    act(() => result.current.approveAnchor(' ', 'entry', 'local-item', 1))
    expect(result.current.approval).toBeNull()
    act(() => result.current.approveAnchor('Text', 'entry'))
    expect(result.current.approval).toBeNull()
  })

  it('retains source context while creating a fresh Council item', () => {
    const { result } = renderHook(() => useSharedFlow())
    act(() => result.current.handleApprove('Old', 'old'))
    act(() => result.current.handleSendToCouncil({ title: 'Cache notes', url: 'https://example.com', body_snippet: 'Source claim' }))
    expect(result.current.councilDraft).toContain('Source: https://example.com')
    expect(result.current.councilDraft).toContain('> Source claim')
    expect(result.current.approval).toBeNull()
  })
})

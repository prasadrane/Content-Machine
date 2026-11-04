import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useCouncilSession } from './useCouncilSession'
import * as councilApi from '../../api/council'
import * as humanizeApi from '../../api/humanize'

vi.mock('../../api/council', () => ({ runCouncil: vi.fn(), getCouncilHistory: vi.fn(), getCouncilSpikes: vi.fn() }))
vi.mock('../../api/humanize', () => ({ runHumanize: vi.fn() }))
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r }); return { promise, resolve } }
const props = (overrides = {}) => ({ draft: 'Original', spikeId: 'first', setDraft: vi.fn(), setSpikeId: vi.fn(), onApprove: vi.fn(), ...overrides })

beforeEach(() => {
  vi.clearAllMocks()
  councilApi.getCouncilSpikes.mockResolvedValue([])
  councilApi.getCouncilHistory.mockResolvedValue({ history: [] })
})

describe('Council request ownership', () => {
  it('does not reuse a review or pending approval for a new item with identical wording and slug', async () => {
    councilApi.runCouncil.mockResolvedValue({ score: 9, draft: 'Original' })
    const initial = props({ councilIdentity: { itemId: 'item-a', version: 1 } })
    const { result, rerender } = renderHook(p => useCouncilSession(p), { initialProps: initial })
    await act(async () => result.current.handleReview({ preventDefault() {} }))
    act(() => result.current.requestApproval('Original', { verdict: 'pass' }))
    rerender({ ...initial, councilIdentity: { itemId: 'item-b', version: 1 } })
    expect(result.current.resultIsEarlier).toBe(true)
    expect(result.current.pendingApproval).toBeNull()
    act(() => result.current.confirmApproval())
    expect(initial.onApprove).not.toHaveBeenCalled()
  })

  it('uses canonical version identity even when text has returned to its original value', async () => {
    councilApi.runCouncil.mockResolvedValue({ score: 9 })
    const initial = props({ councilIdentity: { itemId: 'item-a', version: 1 } })
    const { result, rerender } = renderHook(p => useCouncilSession(p), { initialProps: initial })
    await act(async () => result.current.handleReview({ preventDefault() {} }))
    rerender({ ...initial, councilIdentity: { itemId: 'item-a', version: 3 } })
    expect(result.current.resultIsEarlier).toBe(true)
  })

  it('ignores history arriving after the selected item changed', async () => {
    const first = deferred(), second = deferred()
    councilApi.getCouncilHistory.mockImplementation(slug => slug === 'first' ? first.promise : second.promise)
    const initial = props()
    const { result, rerender } = renderHook(p => useCouncilSession(p), { initialProps: initial })
    rerender({ ...initial, spikeId: 'second' })
    await act(async () => second.resolve({ best: { draft: 'Second history' } }))
    await act(async () => first.resolve({ best: { draft: 'Wrong history' } }))
    expect(result.current.best.draft).toBe('Second history')
  })

  it('keeps a delayed review attached to its submitted version after editing', async () => {
    const response = deferred()
    councilApi.runCouncil.mockReturnValue(response.promise)
    const initial = props()
    const { result, rerender } = renderHook(p => useCouncilSession(p), { initialProps: initial })
    let pending
    act(() => { pending = result.current.handleReview({ preventDefault() {} }) })
    rerender({ ...initial, draft: 'Newer edits' })
    await act(async () => { response.resolve({ score: 9, draft: 'Revised original' }); await pending })
    expect(result.current.result.reviewInput).toMatchObject({ text: 'Original', slug: 'first', version: 0 })
    expect(result.current.resultIsEarlier).toBe(true)
    expect(initial.setDraft).not.toHaveBeenCalled()
  })

  it('does not mistake returning to matching text for the submitted version', async () => {
    councilApi.runCouncil.mockResolvedValue({ score: 9 })
    const initial = props()
    const { result, rerender } = renderHook(p => useCouncilSession(p), { initialProps: initial })
    await act(async () => result.current.handleReview({ preventDefault() {} }))
    rerender({ ...initial, draft: 'Changed' })
    rerender(initial)
    expect(result.current.resultIsEarlier).toBe(true)
  })

  it('cancels pending approval when its item changes', async () => {
    const initial = props()
    const { result, rerender } = renderHook(p => useCouncilSession(p), { initialProps: initial })
    act(() => result.current.requestApproval('Approved original', { verdict: 'pass' }))
    rerender({ ...initial, spikeId: 'second' })
    await waitFor(() => expect(result.current.pendingApproval).toBeNull())
    act(() => result.current.confirmApproval())
    expect(initial.onApprove).not.toHaveBeenCalled()
  })

  it('approves only captured text and captured item', () => {
    const initial = props()
    const { result } = renderHook(p => useCouncilSession(p), { initialProps: initial })
    act(() => result.current.requestApproval('Reviewed text', { verdict: 'pass' }))
    act(() => result.current.confirmApproval())
    expect(initial.onApprove).toHaveBeenCalledWith('Reviewed text', 'first')
  })

  it('retains polish provenance and never replaces newer editor text', async () => {
    const response = deferred()
    humanizeApi.runHumanize.mockReturnValue(response.promise)
    const initial = props()
    const { result, rerender } = renderHook(p => useCouncilSession(p), { initialProps: initial })
    let pending
    act(() => { pending = result.current.handleHumanize('Original') })
    rerender({ ...initial, draft: 'Newer edits' })
    await act(async () => { response.resolve({ text: 'Polished original' }); await pending })
    expect(result.current.humanizedResult.reviewInput).toMatchObject({ text: 'Original', slug: 'first' })
    expect(result.current.polishIsEarlier).toBe(true)
    expect(initial.setDraft).not.toHaveBeenCalled()
  })
})

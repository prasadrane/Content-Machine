import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCopyToClipboard } from './useCopyToClipboard'

beforeEach(() => {
  vi.useFakeTimers()
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: vi.fn(async () => {}) },
  })
})
afterEach(() => vi.useRealTimers())

describe('useCopyToClipboard', () => {
  it('sets copied true then resets after timeout', async () => {
    const { result } = renderHook(() => useCopyToClipboard(2000))
    await act(async () => { await result.current.copy('hello') })
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('hello')
    expect(result.current.copied).toBe(true)
    act(() => { vi.advanceTimersByTime(2000) })
    expect(result.current.copied).toBe(false)
  })
  it('returns false and stays calm when clipboard rejects', async () => {
    navigator.clipboard.writeText.mockRejectedValueOnce(new Error('denied'))
    const { result } = renderHook(() => useCopyToClipboard())
    let ok
    await act(async () => { ok = await result.current.copy('x') })
    expect(ok).toBe(false)
    expect(result.current.copied).toBe(false)
  })
})

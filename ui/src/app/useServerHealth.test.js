import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useServerHealth } from './useServerHealth'
import * as healthApi from '../api/health'

vi.mock('../api/health', () => ({ getHealth: vi.fn() }))

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('useServerHealth', () => {
  it('true when health ok, polls on interval', async () => {
    healthApi.getHealth.mockResolvedValue({ status: 'ok' })
    const { result } = renderHook(() => useServerHealth(10000))
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })
    expect(result.current).toBe(true)
    healthApi.getHealth.mockResolvedValue({ status: 'degraded' })
    await act(async () => { await vi.advanceTimersByTimeAsync(10000) })
    expect(result.current).toBe(false)
    expect(healthApi.getHealth).toHaveBeenCalledTimes(2)
  })
  it('false when fetch rejects', async () => {
    healthApi.getHealth.mockRejectedValue(new Error('down'))
    const { result } = renderHook(() => useServerHealth(10000))
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })
    expect(result.current).toBe(false)
  })
})

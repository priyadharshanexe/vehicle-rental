import { describe, expect, it, vi } from 'vitest'
import { api, queryString } from './api'

describe('API requests', () => {
  it('preserves the session and reports Django field errors', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(
      JSON.stringify({ start_date: ['Choose today or a later date.'] }),
      { status: 400, headers: { 'Content-Type': 'application/json' } },
    ))
    vi.stubGlobal('fetch', fetchMock)
    try {
      await expect(api('bookings/', { method: 'POST' })).rejects.toThrow('start date: Choose today or a later date.')
      expect(fetchMock).toHaveBeenCalledWith('/api/v1/bookings/', { method: 'POST', credentials: 'same-origin' })
    } finally {
      vi.unstubAllGlobals()
    }
  })
  it('keeps only nonempty search values', () => {
    const form = new FormData()
    form.set('location', ' Madurai ')
    form.set('fuel', ' ')
    expect(queryString(form).toString()).toBe('location=Madurai')
  })
})

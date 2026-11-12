import { describe, expect, it, vi } from 'vitest'
import { api, authRequest, queryString } from './api'

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


describe('Account requests', () => {
  it('accepts verification that completes without opening a session', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(
      JSON.stringify({ status: 401, meta: { is_authenticated: false } }), { status: 401 },
    ))
    vi.stubGlobal('fetch', fetchMock)
    try {
      await expect(authRequest('auth/email/verify', { key: 'demo-key' }, 'csrf', { signedOutSuccess: true }))
        .resolves.toBeUndefined()
      expect(fetchMock).toHaveBeenCalledWith('/auth/browser/v1/auth/email/verify', expect.objectContaining({
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': 'csrf' },
      }))
    } finally {
      vi.unstubAllGlobals()
    }
  })
})

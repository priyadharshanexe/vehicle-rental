import { describe, expect, it } from 'vitest'
import type { Vehicle } from './api'
import { featuredListings, overlapsUnavailableDates } from './marketplaceData'

const vehicle: Vehicle = {
  id: 1, name: 'Hyundai i20', vehicle_type: 'Car', fuel_type: 'Petrol',
  location: 'Madurai', price_per_day: '1800.00', vehicle_image: null,
}

describe('featured listings', () => {
  it('prefers different models when available', () => {
    const duplicate = { ...vehicle, id: 2 }
    const other = { ...vehicle, id: 3, name: 'Suzuki Swift' }
    expect(featuredListings([vehicle, duplicate, other])).toEqual([vehicle, other])
    expect(featuredListings([vehicle, duplicate])).toEqual([vehicle, duplicate])
    expect(featuredListings([])).toEqual([])
  })
})

describe('unavailable dates', () => {
  it('includes both ends of the blocked period', () => {
    const blocks = [{ start_date: '2026-11-16', end_date: '2026-11-18' }]
    expect(overlapsUnavailableDates(blocks, '2026-11-15', '2026-11-16')).toBe(true)
    expect(overlapsUnavailableDates(blocks, '2026-11-18', '2026-11-19')).toBe(true)
    expect(overlapsUnavailableDates(blocks, '2026-11-19', '2026-11-20')).toBe(false)
    expect(overlapsUnavailableDates(blocks, '', '2026-11-18')).toBe(false)
  })
})

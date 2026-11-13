import type { DateRange, Vehicle } from './api'

export function featuredListings(vehicles: Vehicle[]) {
  const first = vehicles[0]
  if (!first) return []
  const second = vehicles.find(vehicle => vehicle.name !== first.name) ?? vehicles[1]
  return second ? [first, second] : [first]
}

export function overlapsUnavailableDates(ranges: DateRange[], start: string, end: string) {
  return Boolean(start && end && ranges.some(range => range.start_date <= end && range.end_date >= start))
}

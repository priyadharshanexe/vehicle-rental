export interface Session {
  csrf_token: string
  user: { id: number; name: string } | null
  google_enabled: boolean
}
export interface Vehicle {
  id: number
  name: string
  vehicle_type: 'Car' | 'Bike'
  fuel_type: string
  location: string | null
  price_per_day: string
  vehicle_image: string | null
}
export interface DateRange { start_date: string; end_date: string }
export interface Review { id: number; rating: number; comment: string }
export interface VehicleDetail extends Vehicle {
  unavailable: DateRange[]
  reviews: Review[]
}
export interface FleetVehicle extends Vehicle { is_available: boolean; archived_at: string | null }
export type BookingStatus = 'Pending' | 'Confirmed' | 'Rejected' | 'Expired' | 'Cancelled' | 'In progress' | 'Returned'
export interface Booking extends DateRange {
  id: number
  vehicle: Vehicle
  status: BookingStatus
  total_price: string
  quoted_daily_rate: string | null
  renter_name: string
  picked_up_at: string | null
  returned_at: string | null
  reviewed: boolean
}
export interface Maintenance extends DateRange { id: number; reason: string }
export interface BookingValue { vehicle_id: number; vehicle__name: string; bookings: number; value: string }

function errorMessage(payload: unknown, fallback: string): string {
  if (typeof payload !== 'object' || payload === null) return fallback
  return Object.entries(payload).flatMap(([field, value]: [string, unknown]) => {
    if (typeof value === 'string') return [value]
    if (Array.isArray(value)) return value.filter((item): item is string => typeof item === 'string')
      .map(item => field === '__all__' ? item : `${field.replaceAll('_', ' ')}: ${item}`)
    return []
  }).join(' ') || fallback
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/${path}`, { ...options, credentials: 'same-origin' })
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null)
    throw new Error(errorMessage(payload, `Request failed (${response.status}).`))
  }
  if (response.status === 204 || response.headers.get('Content-Length') === '0') return undefined as T
  return await response.json() as T
}

export const money = (value: string | number) => new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR',
}).format(Number(value))

export function dateLabel(value: string) {
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeZone: 'UTC' })
    .format(new Date(value))
}

export function queryString(form: FormData) {
  const params = new URLSearchParams()
  for (const [key, value] of form) if (typeof value === 'string' && value.trim()) params.set(key, value.trim())
  return params
}

interface AuthError { message?: string }

export async function signIn(email: string, password: string, csrfToken: string) {
  const response = await fetch('/auth/browser/v1/auth/login', {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify({ email, password }),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { errors?: AuthError[] } | null
    throw new Error(body?.errors?.map(error => error.message).filter(Boolean).join(' ')
      || (response.status === 401 ? 'Complete email verification before signing in.' : 'Sign-in failed. Please try again.'))
  }
}

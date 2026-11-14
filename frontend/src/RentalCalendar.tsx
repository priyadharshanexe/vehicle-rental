import { useState } from 'react'
import type { DateRange } from './api'
import { overlapsUnavailableDates } from './marketplaceData'

export function RentalCalendar({ start, end, unavailable, onSelect }: {
  start: string; end: string; unavailable: DateRange[]; onSelect: (start: string, end: string) => void
}) {
  const [today] = useState(() => new Date().toISOString().slice(0, 10))
  const [month, setMonth] = useState(() => new Date((start || today).slice(0, 7) + '-01T00:00:00Z'))
  const year = month.getUTCFullYear()
  const index = month.getUTCMonth()
  const choosingReturn = Boolean(start && !end)
  const days = new Date(Date.UTC(year, index + 1, 0)).getUTCDate()
  const changeMonth = (step: number) => setMonth(new Date(Date.UTC(year, index + step, 1)))
  return <section className="rental-calendar" aria-label="Rental calendar">
    <div className="calendar-header">
      <button type="button" className="secondary" aria-label="Previous month" disabled={month.toISOString().slice(0, 7) <= today.slice(0, 7)} onClick={() => changeMonth(-1)}>‹</button>
      <strong aria-live="polite">{month.toLocaleDateString('en-IN', { month: 'long', year: 'numeric', timeZone: 'UTC' })}</strong>
      <button type="button" className="secondary" aria-label="Next month" onClick={() => changeMonth(1)}>›</button>
    </div>
    <p aria-live="polite">{choosingReturn ? 'Choose your return date' : 'Choose your pickup date'}</p>
    <div className="calendar-days">
      {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(day => <span key={day}>{day}</span>)}
      {Array.from({ length: month.getUTCDay() }, (_, i) => <span key={i} />)}
      {Array.from({ length: days }, (_, i) => {
        const date = new Date(Date.UTC(year, index, i + 1))
        const key = date.toISOString().slice(0, 10)
        const selected = key === start || key === end
        const blocked = overlapsUnavailableDates(unavailable, choosingReturn && key >= start ? start : key, key)
        return <button type="button" key={key} disabled={key < today || blocked}
          aria-label={date.toLocaleDateString('en-IN', { dateStyle: 'full', timeZone: 'UTC' })} aria-pressed={selected}
          data-in-range={Boolean(start && end && key > start && key < end)}
          onClick={() => choosingReturn && key >= start ? onSelect(start, key) : onSelect(key, '')}>{i + 1}</button>
      })}
    </div>
  </section>
}

import { Breadcrumb } from './Breadcrumb'
import { Price, PriceBreakdown } from './Pricing'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, dateLabel } from './api'
import type { Booking } from './api'
import { Busy, Notice, Photo, Status } from './shared'
import { formData, useWrite } from './requests'

const customerQueues: Record<string, Booking['status'][]> = {
  All: [],
  Upcoming: ['Pending', 'Confirmed'],
  Active: ['In progress'],
  Completed: ['Returned'],
  Closed: ['Cancelled', 'Rejected', 'Expired'],
}
const ownerQueues: Record<string, Booking['status'][]> = {
  All: [], Requests: ['Pending'], Pickups: ['Confirmed'], Returns: ['In progress'],
  Completed: ['Returned'], Closed: ['Cancelled', 'Rejected', 'Expired'],
}
const ownerActions: Partial<Record<Booking['status'], [string, string][]>> = {
  Pending: [['approve', 'Approve'], ['reject', 'Reject']],
  Confirmed: [['pickup', 'Record pickup']],
  'In progress': [['return', 'Record return']],
}
export function Bookings({ owner = false }: { owner?: boolean }) {
  const { id } = useParams()
  const [today] = useState(() => new Date().toISOString().slice(0, 10))
  const [queue, setQueue] = useState('All')
  const [review, setReview] = useState<number | null>(null)
  const query = useQuery({ queryKey: [owner ? 'owner-bookings' : 'bookings'], queryFn: () => api<Booking[]>(owner ? 'owner/bookings/' : 'bookings/') })
  const write = useWrite()
  const queues = owner ? ownerQueues : customerQueues
  const statuses = Object.entries(queues).find(([label]) => label === queue)?.[1] ?? []
  const rows = query.data?.filter(row => (!id || String(row.id) === id) && (!statuses.length || statuses.includes(row.status)))
  return <>{id && <Breadcrumb to="/bookings" parent="My bookings" current="Booking details" />}<div className="page-heading"><h1>{owner ? 'Rental requests' : id ? 'Booking details' : 'My bookings'}</h1>
    <p>{owner ? 'Respond to requests and record vehicle handoffs.' : id ? 'Reservation, pricing, and handoff details.' : 'Track your requests, current rentals, and past trips.'}</p></div>
    {!id && <div className="segments" role="group" aria-label="Filter bookings">{Object.entries(queues).map(([label, values]) =>
      <button className="secondary" type="button" key={label} aria-pressed={queue === label} onClick={() => setQueue(label)}>{label}
        {query.data && <span>{query.data.filter(row => !values.length || values.includes(row.status)).length}</span>}</button>)}</div>}
    {query.isPending && <Busy />}<Notice error={query.error} /><Notice error={write.error} />
    {rows?.length === 0 && <p className="empty">{id ? "Booking unavailable." : "No bookings in this view."} {!owner && !id && <Link to="/vehicles">Browse vehicles</Link>}</p>}
    <div className="records">{rows?.map(row => <article className={id ? "booking-detail" : "record booking-row"} key={row.id}>
      {id ? <section className="panel booking-overview">
        <div className="booking-vehicle"><Photo vehicle={row.vehicle} /><div>
          <Status value={row.status} />
          {row.overdue && <strong className="overdue">Overdue return</strong>}
          <h2>{row.vehicle.name}</h2><p>{row.vehicle.vehicle_type} · {row.vehicle.location ?? 'Location on request'}</p>
        </div></div>
        <dl className="booking-dates">
          <div><dt>Pickup date</dt><dd><time dateTime={row.start_date}>{dateLabel(row.start_date)}</time></dd></div>
          <div><dt>Return date</dt><dd><time dateTime={row.end_date}>{dateLabel(row.end_date)}</time></dd></div>
        </dl>
      </section> : <>
        <div className="record-identity"><Photo vehicle={row.vehicle} /><div><h2>{owner ? row.vehicle.name : <Link to={`/bookings/${row.id}`}>{row.vehicle.name}</Link>}</h2><p>{row.vehicle.vehicle_type} · {row.vehicle.location ?? 'Location on request'}</p><p>{dateLabel(row.start_date)} to {dateLabel(row.end_date)}</p>{owner && <p>Renter: {row.renter_name}</p>}</div></div>
        <div><Status value={row.status} />{row.overdue && <strong className="overdue">Overdue return</strong>}<p><Price value={row.total_price} label="Booking total" /></p>
          {row.picked_up_at && <p>Picked up {timestamp(row.picked_up_at)}</p>}
          {row.returned_at && <p>Returned {timestamp(row.returned_at)}</p>}
        </div>
      </>}
      <div className="actions">
        {owner ? ownerActions[row.status]?.filter(([action]) => action !== 'pickup' || (today >= row.start_date && today <= row.end_date)).map(([action, label]) => <button key={action} disabled={write.isPending} onClick={() => write.mutate({ path: `bookings/${row.id}/${action}/` })}>{label}</button>) : <>
          {!id && <Link to={`/bookings/${row.id}`}>View booking</Link>}<a href={`/download-receipt/${row.id}/`}>Booking summary</a>
          {(row.status === 'Pending' || (row.status === 'Confirmed' && row.start_date > today)) && <button className="secondary" disabled={write.isPending} onClick={() => write.mutate({ path: `bookings/${row.id}/cancel/` })}>Cancel booking</button>}
          {row.status === 'Returned' && !row.reviewed && <button className="secondary" onClick={() => setReview(row.id)}>Leave a review</button>}
        </>}
      </div>
      {id && <PriceBreakdown rate={row.quoted_daily_rate}
        days={(Date.parse(row.end_date) - Date.parse(row.start_date)) / 86400000 + 1} total={row.total_price} />}
      {id && <BookingTimeline row={row} />}
      {review === row.id && <form className="fields" onSubmit={event => write.mutate({
        path: `bookings/${row.id}/review/`, body: formData(event),
      }, { onSuccess: () => setReview(null) })}>
        <label>Rating<select name="rating">{[5, 4, 3, 2, 1].map(value => <option key={value}>{value}</option>)}</select></label>
        <label>Comment<textarea name="comment" required maxLength={500} /></label><button disabled={write.isPending}>Publish review</button>
      </form>}
    </article>)}</div>
  </>
}


function timestamp(value: string) {
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function BookingTimeline({ row }: { row: Booking }) {
  const events = [
    { label: 'Picked up', at: row.picked_up_at },
    { label: 'Returned', at: row.returned_at },
  ]
  if (!events.some(event => event.at && event.at === row.status_changed_at)) {
    events.push({ label: row.status, at: row.status_changed_at })
  }
  return <section className="panel booking-timeline"><h3>Booking timeline</h3><ol>
    {events.filter(event => event.at || event.label === row.status).map(event => <li key={event.label}>
      <strong>{event.label}</strong>{event.at && <time dateTime={event.at}>{timestamp(event.at)}</time>}
    </li>)}
  </ol></section>
}

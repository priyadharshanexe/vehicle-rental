import { Price } from './Pricing'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, dateLabel } from './api'
import type { Booking, BookingValue, FleetVehicle } from './api'
import { Busy, Notice, Photo, Status } from './shared'
import { useSession } from './requests'

export function Dashboard({ owner = false }: { owner?: boolean }) {
  const session = useSession()
  const bookings = useQuery({
    queryKey: [owner ? 'owner-bookings' : 'bookings'],
    queryFn: () => api<Booking[]>(owner ? 'owner/bookings/' : 'bookings/'),
  })
  const fleet = useQuery({ queryKey: ['fleet'], queryFn: () => api<FleetVehicle[]>('owner/fleet/'), enabled: owner })
  const values = useQuery({ queryKey: ['values', ''], queryFn: () => api<BookingValue[]>('owner/value/'), enabled: owner })
  const rows = bookings.data ?? []
  const pending = rows.filter(row => row.status === 'Pending')
  const confirmed = rows.filter(row => row.status === 'Confirmed')
  const active = rows.filter(row => row.status === 'In progress')
  const returned = rows.filter(row => row.status === 'Returned')
  const upcoming = [...pending, ...confirmed].sort((a, b) => a.start_date.localeCompare(b.start_date))
  const next = active[0] ?? upcoming[0]
  const recent = [...rows].sort((a, b) => b.id - a.id).slice(0, 4)
  const listings = fleet.data?.filter(row => !row.archived_at)
  const metrics: [string, string | number | React.JSX.Element | undefined][] = owner ? [
    ['Fleet listings', listings?.length], ['Published', listings?.filter(row => row.is_available).length],
    ['Pending requests', bookings.data && pending.length], ['Active rentals', bookings.data && active.length],
    ['Overdue returns', bookings.data && active.filter(row => row.overdue).length],
    ['Completed booking value', values.data && <Price key="completed-value" value={values.data.reduce((sum, row) => sum + Number(row.value), 0)} />],
  ] : [['Upcoming', bookings.data && upcoming.length], ['Active rentals', bookings.data && active.length], ['Completed', bookings.data && returned.length]]
  return <>
    <div className="page-heading section-head"><div><h1>{owner ? 'Fleet overview' : `Welcome, ${session.data?.user?.name ?? 'renter'}`}</h1>
      <p>{owner ? 'Review your listings, requests, and upcoming handoffs.' : 'See what’s coming up and manage your rentals.'}</p></div>
      <Link className="button" to={owner ? '/owner/fleet?edit=new' : '/vehicles'}>{owner ? 'List a vehicle' : 'Browse vehicles'}</Link>
    </div>
    <div className="metrics dashboard-metrics">{metrics.map(([label, value]) => <div key={label}><span>{label}</span>{typeof value === 'object' ? value : <strong>{value ?? '—'}</strong>}</div>)}</div>
    {bookings.isPending && <Busy />}<Notice error={bookings.error ?? fleet.error ?? values.error} />
    <div className="dashboard-grid">
      <section className="panel"><div className="section-head"><h2>{owner ? 'Recent requests' : 'Recent bookings'}</h2>
        <Link to={owner ? '/owner/requests' : '/bookings'}>View all →</Link></div>
        <BookingRows owner={owner} rows={owner ? pending.slice(-4).reverse() : recent} />
      </section>
      <section className="panel"><h2>{owner ? 'Pickup and return schedule' : 'Your next rental'}</h2>
        {owner ? <BookingRows owner rows={[...active, ...confirmed].slice(0, 4)} />
          : next ? <><Photo vehicle={next.vehicle} /><BookingRows rows={[next]} /></> : <p>No upcoming rental. <Link to="/vehicles">Explore vehicles</Link>.</p>}
      </section>
    </div>
    <div className="quick-links">{(owner ? [['/owner/fleet', 'Manage fleet'], ['/owner/maintenance', 'Schedule maintenance'], ['/owner/value', 'View booking value']]
      : [['/bookings', 'Manage bookings'], ['/account', 'Account settings'], ['/vehicles', 'Find a vehicle']]).map(([url, label]) => <Link key={url} to={url}>{label} →</Link>)}</div>
  </>
}

function BookingRows({ rows, owner = false }: { rows: Booking[]; owner?: boolean }) {
  if (!rows.length) return <p className="empty">No bookings to show here.</p>
  return <ul className="dashboard-list">{rows.map(row => <li key={row.id}>
    <div><Link to={owner ? '/owner/requests' : `/bookings/${row.id}`}>{row.vehicle.name}</Link>
      <p>{row.status === 'In progress' ? 'Return' : 'Pickup'} · {dateLabel(row.status === 'In progress' ? row.end_date : row.start_date)}</p></div>
    <Status value={row.status} />
  </li>)}</ul>
}

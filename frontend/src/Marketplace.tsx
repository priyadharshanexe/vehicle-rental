import { Breadcrumb } from './Breadcrumb'
import { Price, PriceBreakdown } from './Pricing'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import type { CSSProperties } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api, dateLabel, queryString } from './api'
import type { Vehicle, VehicleDetail } from './api'
import { Busy, Notice, Photo } from './shared'
import { formData, useSession, useWrite } from './requests'
import { featuredListings, overlapsUnavailableDates } from './marketplaceData'
import heroImage from './assets/marketplace-hero.webp'

function Search({ params, compact = false }: { params?: URLSearchParams; compact?: boolean }) {
  const navigate = useNavigate()
  return <form className="filters" key={params?.toString()} onSubmit={event => navigate(`/vehicles?${queryString(formData(event))}`)}>
    <label>Location<input name="location" placeholder="City or area" defaultValue={params?.get('location') ?? ''} /></label>
    <label>Pickup date<input type="date" name="start_date" defaultValue={params?.get('start_date') ?? ''} /></label>
    <label>Return date<input type="date" name="end_date" defaultValue={params?.get('end_date') ?? ''} /></label>
    {!compact && <label>Vehicle name<input name="q" defaultValue={params?.get('q') ?? ''} /></label>}
      <label>Type<select name="type" defaultValue={params?.get('type') ?? ''}><option value="">All types</option><option>Car</option><option>Bike</option></select></label>
    {!compact && <label>Fuel<input name="fuel" defaultValue={params?.get('fuel') ?? ''} /></label>}
    <button>Find vehicles</button>
  </form>
}


export function Home() {
  const cars = useQuery({ queryKey: ['vehicles', 'type=Car'], queryFn: () => api<CatalogResult>('vehicles/?type=Car') })
  const bikes = useQuery({ queryKey: ['vehicles', 'type=Bike'], queryFn: () => api<CatalogResult>('vehicles/?type=Bike') })
  return <>
    <section className="hero" style={{ '--hero-image': `url(${heroImage})` } as CSSProperties}>
      <div className="hero-copy"><h1>Find your next ride.</h1><p>Rent a car or bike from a local owner. Pick a place and dates to see what’s available.</p></div>
      <Search compact />
    </section>
    <section className="featured">
      <div className="section-head"><h2>Featured vehicles</h2><Link className="button secondary" to="/vehicles">Browse all vehicles</Link></div>
      {(cars.isPending || bikes.isPending) && <Busy />}<Notice error={cars.error ?? bikes.error} />
      <div className="featured-grid">
        {[{ title: 'Cars', type: 'Car', result: cars.data }, { title: 'Bikes', type: 'Bike', result: bikes.data }].map(group =>
          <section className="featured-category" data-vehicle-type={group.type} key={group.type}><h3 className="category-head">{group.title}</h3>
            {group.result?.results.length === 0 && <p className="empty">No published listings in this category yet.</p>}
            <div className="cards">{featuredListings(group.result?.results ?? []).map(vehicle => <Listing key={vehicle.id} vehicle={vehicle} />)}</div>
          </section>)}
      </div>
    </section>
    <section className="how"><h2>How renting works</h2><ol>
      <li><strong>Find a vehicle</strong><p>Filter by location, vehicle type, and the dates you need.</p></li>
      <li><strong>Send a request</strong><p>Check the total before requesting. The owner has up to 24 hours to respond.</p></li>
      <li><strong>Pick up and return</strong><p>Track confirmation and handoffs in My bookings.</p></li>
    </ol></section>
    <section className="owner-callout"><div><h2>Have a vehicle to rent?</h2><p>Publish your listing, set your rate, and manage requests in one place.</p></div>
      <Link className="button" to="/owner/fleet?edit=new">List your vehicle</Link></section>
  </>
}

type CatalogResult = { count: number; next: string | null; previous: string | null; results: Vehicle[] }

function Listing({ vehicle, params = '' }: { vehicle: Vehicle; params?: string }) {
  const url = `/vehicles/${vehicle.id}${params ? `?${params}` : ''}`
  const dates = new URLSearchParams(params)
  return <article className="listing" data-vehicle-type={vehicle.vehicle_type}>
    <Link to={url} className="listing-card-link" aria-label={`View details for ${vehicle.name}`}>
      <div className="listing-photo"><Photo vehicle={vehicle} /><span>{vehicle.vehicle_type}</span></div>
      <div className="listing-body"><h3>{vehicle.name}</h3><p>{vehicle.location ?? 'Location on request'} · {vehicle.fuel_type}</p>
        {dates.has('start_date') && dates.has('end_date') && <p className="availability">Matches your dates</p>}
        <div className="listing-bottom"><Price value={vehicle.price_per_day} label="/ day" /><span className="listing-arrow" aria-hidden="true">→</span></div>
      </div>
    </Link>
  </article>
}

export function Catalog() {
  const [params, setParams] = useSearchParams()
  const page = Number(params.get('page') || 1)
  const goToPage = (target: number) => {
    const next = new URLSearchParams(params)
    next.set('page', String(target))
    setParams(next)
  }
  const query = useQuery({ queryKey: ['vehicles', params.toString()], queryFn: () => api<CatalogResult>(`vehicles/?${params}`) })
  return <><div className="page-heading"><h1>{params.get('type') === 'Car' ? 'Browse cars' : params.get('type') === 'Bike' ? 'Browse bikes' : 'Browse vehicles'}</h1></div><div className="catalog"><aside><details className="mobile-filters"><summary>Filters</summary><Search params={params} /><Link to="/vehicles">Clear filters</Link></details><div className="desktop-filters"><h2>Filters</h2><Search params={params} /><Link to="/vehicles">Clear filters</Link></div></aside><section>
    {query.isPending && <Busy />}<Notice error={query.error} />
    <div className="cards">{query.data?.results.map(vehicle => <Listing key={vehicle.id} vehicle={vehicle} params={params.toString()} />)}</div>
    {query.data?.count === 0 && <p className="empty">No matching vehicles. <Link to="/vehicles">Clear filters</Link>.</p>}
    {(query.data?.previous || query.data?.next) && <nav className="actions" aria-label="Catalog pages">
      {query.data.previous && <button className="secondary" onClick={() => goToPage(page - 1)}>Previous</button>}
      <span>Page {page}</span>
      {query.data.next && <button className="secondary" onClick={() => goToPage(page + 1)}>Next</button>}
    </nav>}
  </section></div></>
}

export function VehiclePage() {
  const { id } = useParams()
  const [params] = useSearchParams()
  return <VehicleReservation key={`${id}:${params}`} id={id} params={params} />
}

function VehicleReservation({ id, params }: { id: string | undefined; params: URLSearchParams }) {
  const [start, setStart] = useState(params.get('start_date') ?? '')
  const [end, setEnd] = useState(params.get('end_date') ?? '')
  const quoteParams = new URLSearchParams({ start_date: start, end_date: end })
  const query = useQuery({ queryKey: ['vehicle', id], queryFn: () => api<VehicleDetail>(`vehicles/${id}/`) })
  const blocked = overlapsUnavailableDates(query.data?.unavailable ?? [], start, end) && start <= end
  const reversed = Boolean(start && end && end < start)
  const canQuote = Boolean(query.data && start && end && !blocked && !reversed)
  const quote = useQuery({
    queryKey: ['quote', id, start, end], enabled: canQuote, staleTime: 30_000,
    queryFn: ({ signal }) => api<{ days: number; total_price: string }>(`vehicles/${id}/quote/?${quoteParams}`, { signal }),
  })
  const session = useSession()
  const write = useWrite<{ id: number }>()
  const navigate = useNavigate()
  const location = useLocation()
  if (query.isPending) return <Busy />
  if (query.isError) return <Notice error={query.error} />
  const vehicle = query.data
  const ready = canQuote && Boolean(quote.data) && !quote.isError
  const alternativeDates = new URLSearchParams(quoteParams)
  alternativeDates.set('type', vehicle.vehicle_type)
  const bookingLabel = write.isPending ? 'Sending request…'
    : blocked ? 'Dates unavailable'
    : !start || !end ? 'Choose rental dates'
    : reversed ? 'Check return date'
    : quote.isError ? 'Quote unavailable'
    : !ready ? 'Getting quote…'
    : 'Request booking'
  return <><Breadcrumb to={params.size ? `/vehicles?${params}` : "/vehicles"} parent="Browse vehicles" current={vehicle.name} />
    <div className="detail"><section className="vehicle-intro">
      <div className="listing-host">
        <span className="listing-host-avatar" aria-hidden="true">{vehicle.host_name?.[0]?.toUpperCase() ?? '–'}</span>
        <div><span>Listed by</span><strong>{vehicle.host_name || 'Owner name unavailable'}</strong></div>
      </div>
      <div className="page-heading"><h1>{vehicle.name}</h1><p className="vehicle-location"><span className="location-pin" aria-hidden="true" />{vehicle.location ?? 'Location on request'}</p></div>
      <Photo vehicle={vehicle} /></section>
    <section className="panel reservation"><h2><Price value={vehicle.price_per_day} label="/ day" /></h2>
      <p>Pickup and return dates are included. The owner has up to 24 hours to respond.</p>
      <form className="fields" onSubmit={event => {
        const fields = formData(event)
        if (!session.data?.user || !ready || write.isPending) return
        write.mutate({
          path: 'bookings/', body: { vehicle_id: vehicle.id, ...Object.fromEntries(fields) },
        }, { onSuccess: booking => navigate(`/bookings/${booking.id}`) })
      }}>
        <label>Pickup date<input name="start_date" type="date" value={start} onInput={event => setStart(event.currentTarget.value)} required /></label>
        <label>Return date<input name="end_date" type="date" value={end} onInput={event => setEnd(event.currentTarget.value)} required /></label>
        <div aria-live="polite">
          {blocked && <div className="quote quote-unavailable"><strong className="availability-label">Unavailable for these dates</strong><p>Choose different dates or browse other vehicles.</p>
            <Link to={`/vehicles?${alternativeDates}`}>Find another vehicle for these dates</Link></div>}
          {reversed && <p>Choose a return date on or after pickup.</p>}
          {ready && quote.data && <>
            <div className="quote quote-available"><strong className="availability-label">Available for these dates</strong></div>
            <PriceBreakdown rate={vehicle.price_per_day} days={quote.data.days} total={quote.data.total_price} estimate />
          </>}
        </div>
        {canQuote && quote.isError && <><Notice error={quote.error} />
          <button className="secondary" type="button" disabled={quote.isFetching} onClick={() => void quote.refetch()}>Retry quote</button></>}
        <Notice error={write.error ?? session.error} />
        {session.data?.user ? <button disabled={write.isPending || !ready}>{bookingLabel}</button>
          : session.data && !blocked && <Link className="button" to={`/sign-in?next=${encodeURIComponent(location.pathname + '?' + quoteParams)}`}>Sign in to request</Link>}
      </form>
    </section>
    <section className="vehicle-information"><div className="vehicle-specs"><h2>Vehicle information</h2>
      <dl><div><dt>Category</dt><dd>{vehicle.vehicle_type}</dd></div><div><dt>Fuel</dt><dd>{vehicle.fuel_type}</dd></div></dl></div>
      {vehicle.unavailable.length > 0 ? <details><summary>Unavailable dates</summary><ul>{vehicle.unavailable.map((range, index) => <li key={index}>{dateLabel(range.start_date)} to {dateLabel(range.end_date)}</li>)}</ul></details> : <p>No unavailable periods are listed. Enter dates to check your rental.</p>}
      <h2>Verified rental reviews</h2>{vehicle.reviews.length ? vehicle.reviews.map(review => <p className="review" key={review.id}><strong>{review.rating}/5</strong> {review.comment}</p>) : <p>No reviews yet.</p>}
    </section>
    </div></>
}

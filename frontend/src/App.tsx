import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import heroImage from './assets/marketplace-hero.webp'
import type { FormEvent, ReactNode } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api, dateLabel, money, queryString, signIn } from './api'
import type { Booking, BookingValue, FleetVehicle, Maintenance, Session, Vehicle, VehicleDetail } from './api'

const useSession = () => useQuery({ queryKey: ['session'], queryFn: () => api<Session>('session/') })
const message = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'
const formData = (event: FormEvent<HTMLFormElement>) => {
  event.preventDefault()
  return new FormData(event.currentTarget)
}

function useWrite() {
  const session = useSession()
  const cache = useQueryClient()
  return useMutation({
    mutationFn: async ({ path, method = 'POST', body }: { path: string; method?: string; body?: FormData | Record<string, unknown> }) => {
      const headers = new Headers({ 'X-CSRFToken': session.data?.csrf_token ?? '' })
      if (body && !(body instanceof FormData)) headers.set('Content-Type', 'application/json')
      return api<unknown>(path, { method, headers, body: body instanceof FormData ? body : body && JSON.stringify(body) })
    },
    onSuccess: () => cache.invalidateQueries({ predicate: query => query.queryKey[0] !== 'session' }),
  })
}

function Notice({ error }: { error: unknown }) {
  return error ? <p className="error" role="alert">{message(error)}</p> : null
}
function Busy() { return <p role="status">Loading…</p> }
function RequireSession({ children }: { children: ReactNode }) {
  const session = useSession()
  const location = useLocation()
  if (session.isPending) return <Busy />
  if (session.isError) return <Notice error={session.error} />
  return session.data.user ? children : <Navigate to={`/sign-in?next=${encodeURIComponent(location.pathname + location.search)}`} replace />
}
function Layout({ children }: { children: ReactNode }) {
  const session = useSession()
  return <>
    <a className="skip" href="#main">Skip to content</a>
    <header><nav className="wrap navigation" aria-label="Main navigation">
      <Link className="brand" to="/">Vehicle Rental</Link>
      <div className="nav-links">
        <Link to="/vehicles">Browse</Link>
        {session.data?.user ? <>
          <Link to="/bookings">My bookings</Link>
          <a href="/accounts/email/">Account</a>
          <details><summary>Owner workspace</summary><div className="menu">
            <Link to="/owner/requests">Rental requests</Link><Link to="/owner/fleet">Fleet</Link>
            <Link to="/owner/value">Booking value</Link>
          </div></details>
          <form method="post" action="/accounts/logout/">
            <input type="hidden" name="csrfmiddlewaretoken" value={session.data.csrf_token} />
            <input type="hidden" name="next" value="/app/" />
            <button className="text-button">Sign out</button>
          </form>
        </> : <Link to="/sign-in">Sign in</Link>}
      </div>
    </nav></header>
    <main className="wrap" id="main">{children}</main>
    <footer><div className="wrap">Vehicle Rental</div></footer>
  </>
}

function SignIn() {
  const session = useSession()
  const [params] = useSearchParams()
  const cache = useQueryClient()
  const login = useMutation({
    mutationFn: (data: FormData) => signIn(String(data.get('email')), String(data.get('password')), session.data?.csrf_token ?? ''),
    onSuccess: () => cache.invalidateQueries({ queryKey: ['session'] }),
  })
  const desired = params.get('next')
  const safe = desired?.startsWith('/') && !desired.startsWith('//') && !desired.includes('\\') ? desired : '/bookings'
  const next = `/app${safe}`
  if (session.isPending) return <Busy />
  if (session.isError) return <Notice error={session.error} />
  if (session.data.user) return <Navigate to={safe} replace />
  return <section className="panel narrow"><h1>Sign in</h1>
    <form onSubmit={event => login.mutate(formData(event))} className="fields">
      <label>Email<input type="email" name="email" autoComplete="email" required /></label>
      <label>Password<input type="password" name="password" autoComplete="current-password" required /></label>
      <Notice error={login.error} /><button disabled={login.isPending}>Sign in</button>
    </form>
    {session.data.google_enabled && <form method="post" action="/accounts/google/login/" className="google">
      <input type="hidden" name="csrfmiddlewaretoken" value={session.data.csrf_token} />
      <input type="hidden" name="next" value={next} />
      <button className="secondary">Continue with Google</button>
    </form>}
    <p><a href="/accounts/password/reset/">Forgot your password?</a></p>
    <p><a href={`/accounts/signup/?next=${encodeURIComponent(next)}`}>Create an account</a></p>
  </section>
}

function Search({ params, compact = false }: { params?: URLSearchParams; compact?: boolean }) {
  const navigate = useNavigate()
  return <form className="filters" key={params?.toString()} onSubmit={event => navigate(`/vehicles?${queryString(formData(event))}`)}>
    <label>Location<input name="location" placeholder="City or area" defaultValue={params?.get('location') ?? ''} /></label>
    <label>Pickup date<input type="date" name="start_date" defaultValue={params?.get('start_date') ?? ''} /></label>
    <label>Return date<input type="date" name="end_date" defaultValue={params?.get('end_date') ?? ''} /></label>
    {!compact && <>
      <label>Vehicle name<input name="q" defaultValue={params?.get('q') ?? ''} /></label>
      <label>Type<select name="type" defaultValue={params?.get('type') ?? ''}><option value="">All types</option><option>Car</option><option>Bike</option></select></label>
      <label>Fuel<input name="fuel" defaultValue={params?.get('fuel') ?? ''} /></label>
    </>}
    <button>Find vehicles</button>
  </form>
}

function Home() {
  return <><section className="hero">
    <div className="hero-intro">
      <div><h1>Find a car or bike for your next trip.</h1>
        <p>Search local listings, check your dates, and request a rental from the vehicle owner.</p></div>
      <div className="hero-art"><img src={heroImage} alt="A compact car and scooter parked along a countryside road" /></div>
    </div>
    <Search compact />
  </section><section className="owner-callout"><h2>Have a vehicle to rent?</h2><p>Manage listings, requests, pickups, and returns in your owner workspace.</p><Link className="button secondary" to="/owner/fleet">Open owner workspace</Link></section></>
}

function Photo({ vehicle }: { vehicle: Vehicle }) {
  return vehicle.vehicle_image
    ? <img className="photo" src={vehicle.vehicle_image} alt={vehicle.name} loading="lazy" />
    : <div className="photo placeholder">{vehicle.vehicle_type}</div>
}

function Catalog() {
  const [params, setParams] = useSearchParams()
  const page = Number(params.get('page') || 1)
  const goToPage = (target: number) => {
    const next = new URLSearchParams(params)
    next.set('page', String(target))
    setParams(next)
  }
  const query = useQuery({ queryKey: ['vehicles', params.toString()], queryFn: () => api<{ count: number; next: string | null; previous: string | null; results: Vehicle[] }>(`vehicles/?${params}`) })
  return <><h1>Browse vehicles</h1><Search params={params} />
    {query.isPending && <Busy />}<Notice error={query.error} />
    {query.data && <p>{query.data.count} matching vehicles</p>}
    <div className="cards">{query.data?.results.map(vehicle => <article className="listing" key={vehicle.id}>
      <Photo vehicle={vehicle} /><div className="listing-body">
        <h2>{vehicle.name}</h2><p>{vehicle.vehicle_type} · {vehicle.fuel_type} · {vehicle.location ?? 'Location on request'}</p>
        <p><strong>{money(vehicle.price_per_day)}</strong> / day</p>
        <Link className="button secondary" to={`/vehicles/${vehicle.id}?${params}`}>View {vehicle.name}</Link>
      </div>
    </article>)}</div>
    {query.data?.count === 0 && <p>No matching vehicles. <Link to="/vehicles">Clear filters</Link>.</p>}
    {(query.data?.previous || query.data?.next) && <nav className="actions" aria-label="Catalog pages">
      {query.data.previous && <button className="secondary" onClick={() => goToPage(page - 1)}>Previous</button>}
      <span>Page {page}</span>
      {query.data.next && <button className="secondary" onClick={() => goToPage(page + 1)}>Next</button>}
    </nav>}
  </>
}

function VehiclePage() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const [start, setStart] = useState(params.get('start_date') ?? '')
  const [end, setEnd] = useState(params.get('end_date') ?? '')
  const quoteParams = new URLSearchParams({ start_date: start, end_date: end })
  const quote = useQuery({
    queryKey: ['quote', id, start, end], enabled: Boolean(start && end),
    queryFn: () => api<{ days: number; total_price: string }>(`vehicles/${id}/quote/?${quoteParams}`),
  })
  const query = useQuery({ queryKey: ['vehicle', id], queryFn: () => api<VehicleDetail>(`vehicles/${id}/`) })
  const session = useSession()
  const write = useWrite()
  const navigate = useNavigate()
  const location = useLocation()
  if (query.isPending) return <Busy />
  if (query.isError) return <Notice error={query.error} />
  const vehicle = query.data
  return <><Link to={`/vehicles?${params}`}>Back to results</Link>
    <div className="detail"><section><h1>{vehicle.name}</h1><Photo vehicle={vehicle} />
      <p>{vehicle.vehicle_type} · {vehicle.fuel_type} · {vehicle.location ?? 'Location on request'}</p>
      {vehicle.unavailable.length > 0 && <details><summary>Unavailable dates</summary><ul>{vehicle.unavailable.map((range, index) => <li key={index}>{dateLabel(range.start_date)} to {dateLabel(range.end_date)}</li>)}</ul></details>}
      <h2>Verified rental reviews</h2>{vehicle.reviews.length ? vehicle.reviews.map(review => <p key={review.id}><strong>{review.rating}/5</strong> {review.comment}</p>) : <p>No reviews yet.</p>}
    </section><section className="panel"><h2>{money(vehicle.price_per_day)} <small>/ day</small></h2>
      <p>Pickup and return dates are included. The owner has up to 24 hours to respond.</p>
      {session.data?.user ? <form className="fields" onSubmit={event => write.mutate({
        path: 'bookings/', body: { vehicle_id: vehicle.id, ...Object.fromEntries(formData(event)) },
      }, { onSuccess: () => navigate('/bookings') })}>
        <label>Pickup date<input name="start_date" type="date" value={start} onInput={event => setStart(event.currentTarget.value)} required /></label>
        <label>Return date<input name="end_date" type="date" value={end} onInput={event => setEnd(event.currentTarget.value)} required /></label>
        <div aria-live="polite">{quote.data && <p>{quote.data.days} day{quote.data.days === 1 ? '' : 's'} · <strong>{money(quote.data.total_price)}</strong></p>}</div>
        <Notice error={quote.error} /><Notice error={write.error} /><button disabled={write.isPending}>Request booking</button>
      </form> : <Link className="button" to={`/sign-in?next=${encodeURIComponent(location.pathname + location.search)}`}>Sign in to request</Link>}
    </section></div></>
}

const ownerActions: Partial<Record<Booking['status'], [string, string][]>> = {
  Pending: [['approve', 'Approve'], ['reject', 'Reject']],
  Confirmed: [['pickup', 'Record pickup']],
  'In progress': [['return', 'Record return']],
}
function Bookings({ owner = false }: { owner?: boolean }) {
  const [queue, setQueue] = useState('all')
  const [review, setReview] = useState<number | null>(null)
  const query = useQuery({ queryKey: [owner ? 'owner-bookings' : 'bookings'], queryFn: () => api<Booking[]>(owner ? 'owner/bookings/' : 'bookings/') })
  const write = useWrite()
  const rows = query.data?.filter(row => queue === 'all' || row.status === queue)
  return <><h1>{owner ? 'Rental requests' : 'My bookings'}</h1>
    {owner && <label className="queue">Queue<select value={queue} onChange={event => setQueue(event.target.value)}>
      <option value="all">All bookings</option><option value="Pending">Requests</option>
      <option value="Confirmed">Pickups</option><option value="In progress">Returns</option>
    </select></label>}
    {query.isPending && <Busy />}<Notice error={query.error} /><Notice error={write.error} />
    {rows?.length === 0 && <p>No bookings in this view.</p>}
    <div className="records">{rows?.map(row => <article className="record" key={row.id}>
      <div><h2>{row.vehicle.name}</h2><p>{dateLabel(row.start_date)} to {dateLabel(row.end_date)}</p>{owner && <p>Renter: {row.renter_name}</p>}</div>
      <div><span className="status">{row.status}</span><p>{money(row.total_price)}</p>
        {row.picked_up_at && <p>Picked up {dateLabel(row.picked_up_at)}</p>}
        {row.returned_at && <p>Returned {dateLabel(row.returned_at)}</p>}
      </div>
      <div className="actions">
        {owner ? ownerActions[row.status]?.map(([action, label]) => <button key={action} disabled={write.isPending} onClick={() => write.mutate({ path: `bookings/${row.id}/${action}/` })}>{label}</button>) : <>
          <a href={`/download-receipt/${row.id}/`}>Booking summary</a>
          {['Pending', 'Confirmed'].includes(row.status) && <button className="secondary" disabled={write.isPending} onClick={() => write.mutate({ path: `bookings/${row.id}/cancel/` })}>Cancel booking</button>}
          {row.status === 'Returned' && !row.reviewed && <button className="secondary" onClick={() => setReview(row.id)}>Leave a review</button>}
        </>}
      </div>
      {review === row.id && <form className="fields" onSubmit={event => write.mutate({
        path: `bookings/${row.id}/review/`, body: formData(event),
      }, { onSuccess: () => setReview(null) })}>
        <label>Rating<select name="rating">{[5, 4, 3, 2, 1].map(value => <option key={value}>{value}</option>)}</select></label>
        <label>Comment<textarea name="comment" required maxLength={500} /></label><button disabled={write.isPending}>Publish review</button>
      </form>}
    </article>)}</div>
  </>
}

function Fleet() {
  const query = useQuery({ queryKey: ['fleet'], queryFn: () => api<FleetVehicle[]>('owner/fleet/') })
  const write = useWrite()
  const [editing, setEditing] = useState<FleetVehicle | 'new' | null>(null)
  const vehicle = editing && editing !== 'new' ? editing : undefined
  return <><div className="section-head"><h1>My fleet</h1><button onClick={() => setEditing('new')}>List a vehicle</button></div>
    {query.isPending && <Busy />}<Notice error={query.error} /><Notice error={write.error} />
    {editing && <section className="panel narrow"><h2>{vehicle ? `Edit ${vehicle.name}` : 'New vehicle'}</h2>
      <form className="fields" key={vehicle?.id ?? 'new'} onSubmit={event => {
        const body = formData(event)
        const image = body.get('vehicle_image')
        if (image instanceof File && !image.size) body.delete('vehicle_image')
        write.mutate({ path: vehicle ? `owner/fleet/${vehicle.id}/` : 'owner/fleet/', method: vehicle ? 'PATCH' : 'POST', body }, { onSuccess: () => setEditing(null) })
      }}>
        <label>Vehicle name<input name="name" required maxLength={100} defaultValue={vehicle?.name} /></label>
        <label>Type<select name="vehicle_type" defaultValue={vehicle?.vehicle_type}><option>Car</option><option>Bike</option></select></label>
        <label>Fuel<input name="fuel_type" required maxLength={50} defaultValue={vehicle?.fuel_type} /></label>
        <label>Location<input name="location" maxLength={100} defaultValue={vehicle?.location ?? ''} /></label>
        <label>Daily rate (INR)<input type="number" name="price_per_day" min=".01" step=".01" required defaultValue={vehicle?.price_per_day} /></label>
        <label>Vehicle photo<input type="file" name="vehicle_image" accept="image/jpeg,image/png,image/webp" required={!vehicle} /></label>
        <div className="actions"><button disabled={write.isPending}>Save vehicle</button><button type="button" className="secondary" onClick={() => setEditing(null)}>Cancel</button></div>
      </form>
    </section>}
    {query.data?.length === 0 && <p>Your vehicles will appear here after you create a listing.</p>}
    <div className="records">{query.data?.map(item => <article className="record" key={item.id}>
      <div><h2>{item.name}</h2><p>{item.vehicle_type} · {item.location ?? 'Location on request'}</p></div>
      <div><span className="status">{item.archived_at ? 'Archived' : item.is_available ? 'Published' : 'Unpublished'}</span><p>{money(item.price_per_day)} / day</p></div>
      {!item.archived_at && <div className="actions">
        <button className="secondary" onClick={() => setEditing(item)}>Edit</button>
        <Link to={`/owner/fleet/${item.id}/maintenance`}>Maintenance</Link>
        <button className="secondary" disabled={write.isPending} onClick={() => write.mutate({
          path: `owner/fleet/${item.id}/`, method: 'PATCH', body: { is_available: !item.is_available },
        })}>{item.is_available ? 'Unpublish' : 'Publish'}</button>
        <button className="secondary" disabled={write.isPending} onClick={() => {
          if (window.confirm(`Archive ${item.name}? Its booking history will be kept.`))
            write.mutate({ path: `owner/fleet/${item.id}/`, method: 'DELETE' })
        }}>Archive</button>
      </div>}
    </article>)}</div>
  </>
}

function MaintenancePage() {
  const { id } = useParams()
  const path = `owner/fleet/${id}/maintenance/`
  const query = useQuery({ queryKey: ['maintenance', id], queryFn: () => api<Maintenance[]>(path) })
  const write = useWrite()
  return <><Link to="/owner/fleet">Back to fleet</Link><h1>Maintenance</h1>
    <section className="panel narrow"><form className="fields" onSubmit={event => write.mutate({ path, body: formData(event) })}>
      <label>Start date<input type="date" name="start_date" required /></label>
      <label>End date<input type="date" name="end_date" required /></label>
      <label>Reason<input name="reason" maxLength={120} required /></label>
      <button disabled={write.isPending}>Block dates</button>
    </form></section>
    {query.isPending && <Busy />}<Notice error={query.error} /><Notice error={write.error} />
    {query.data?.length === 0 && <p>No maintenance scheduled.</p>}
    <ul className="records">{query.data?.map(block => <li className="record" key={block.id}>
      <div>{block.reason}<p>{dateLabel(block.start_date)} to {dateLabel(block.end_date)}</p></div>
      <button className="secondary" disabled={write.isPending} onClick={() => write.mutate({ path: `${path}${block.id}/`, method: 'DELETE' })}>Remove block</button>
    </li>)}</ul>
  </>
}
function Values() {
  const [params, setParams] = useSearchParams()
  const query = useQuery({ queryKey: ['values', params.toString()], queryFn: () => api<BookingValue[]>(`owner/value/?${params}`) })
  return <><h1>Completed booking value</h1>
    <form className="filters" onSubmit={event => setParams(queryString(formData(event)))}>
      <label>From<input type="date" name="start_date" defaultValue={params.get('start_date') ?? ''} /></label>
      <label>To<input type="date" name="end_date" defaultValue={params.get('end_date') ?? ''} /></label><button>Filter</button>
    </form>
    {query.isPending && <Busy />}<Notice error={query.error} />
    {query.data && <><p>Total <strong>{money(query.data.reduce((total, row) => total + Number(row.value), 0))}</strong></p>
      {query.data.length === 0 ? <p>No completed bookings for this period.</p> : <div className="records">
        {query.data.map(row => <article className="record" key={row.vehicle_id}><h2>{row.vehicle__name}</h2><p>{row.bookings} completed</p><p>{money(row.value)}</p></article>)}
      </div>}
    </>}
  </>
}

export default function App() {
  return <BrowserRouter basename="/app"><Layout><Routes>
    <Route index element={<Home />} /><Route path="vehicles" element={<Catalog />} />
    <Route path="vehicles/:id" element={<VehiclePage />} /><Route path="sign-in" element={<SignIn />} />
    <Route path="bookings" element={<RequireSession><Bookings /></RequireSession>} />
    <Route path="owner/requests" element={<RequireSession><Bookings owner /></RequireSession>} />
    <Route path="owner/fleet" element={<RequireSession><Fleet /></RequireSession>} />
    <Route path="owner/fleet/:id/maintenance" element={<RequireSession><MaintenancePage /></RequireSession>} />
    <Route path="owner/value" element={<RequireSession><Values /></RequireSession>} />
    <Route path="*" element={<><h1>Page not found</h1><Link to="/">Return home</Link></>} />
  </Routes></Layout></BrowserRouter>
}

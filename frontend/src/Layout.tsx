import type { ReactNode } from 'react'
import { Link, NavLink, Navigate, useLocation } from 'react-router-dom'
import { Busy, Notice } from './shared'
import { useSession } from './requests'
import RouteErrorBoundary from './RouteErrorBoundary'

export function RequireSession({ children }: { children: ReactNode }) {
  const session = useSession()
  const location = useLocation()
  if (session.isPending) return <Busy />
  if (session.isError) return <Notice error={session.error} />
  return session.data.user ? children : <Navigate to={`/sign-in?next=${encodeURIComponent(location.pathname + location.search)}`} replace />
}

const ownerLinks = [
  ['/owner', 'Overview'], ['/owner/requests', 'Rental requests'], ['/owner/fleet', 'Fleet'],
  ['/owner/maintenance', 'Maintenance'], ['/owner/value', 'Booking value'], ['/account', 'Account settings'],
]
const customerLinks = [
  ['/dashboard', 'Overview'], ['/bookings', 'My bookings'], ['/account', 'Account settings'], ['/vehicles', 'Browse vehicles'],
]

export function Layout({ children }: { children: ReactNode }) {
  const { data } = useSession()
  const { pathname, key } = useLocation()
  const owner = pathname.startsWith('/owner')
  const workspace = owner || ['/dashboard', '/bookings', '/account'].some(path => pathname.startsWith(path))
  return <>
    <a className="skip" href="#main">Skip to content</a>
    <header className="site-header"><nav className="wrap navigation" aria-label="Main navigation">
      <Link className="brand" to="/"><span className="brand-mark" aria-hidden="true">M</span> Motorlane</Link>
      <div className="nav-links">
        <NavLink end to="/">Discover</NavLink><Link to="/vehicles?type=Car">Browse cars</Link><Link to="/vehicles?type=Bike">Browse bikes</Link>
      </div>
      <div className="actions"><Link className="host-link" to="/owner/fleet?edit=new">List your vehicle</Link>
        {data?.user ? <details className="account-menu"><summary>Account</summary><div className="menu">
          <Link to="/dashboard">Renter dashboard</Link><Link to="/owner">Owner workspace</Link><Link to="/account">Settings</Link>
          <form method="post" action="/accounts/logout/">
            <input type="hidden" name="csrfmiddlewaretoken" value={data.csrf_token} />
            <input type="hidden" name="next" value="/app/" /><button className="secondary">Sign out</button>
          </form>
        </div></details> : <Link className="button secondary" to="/sign-in">Sign in</Link>}
      </div>
    </nav></header>
    <main className={workspace && data?.user ? 'wrap workspace' : 'wrap'} id="main">
      {workspace && data?.user && <aside className="workspace-nav">
        <strong>{owner ? 'Owner workspace' : 'Renter workspace'}</strong>
        <nav aria-label={owner ? 'Owner navigation' : 'Renter navigation'}>
          {(owner ? ownerLinks : customerLinks).map(([url, label]) => <NavLink end={url === '/owner' || url === '/owner/fleet'} key={url} to={url}>{label}</NavLink>)}
        </nav>
      </aside>}
      <div className="page-content"><RouteErrorBoundary key={key}>{children}</RouteErrorBoundary></div>
    </main>
    <footer><div className="wrap footer-grid"><div><Link className="brand" to="/">Motorlane</Link><p>Local car and bike rentals.</p></div>
      <nav aria-label="Footer navigation"><Link to="/vehicles">All vehicles</Link><Link to="/vehicles?type=Car">Cars</Link><Link to="/vehicles?type=Bike">Bikes</Link><Link to="/owner">Owner workspace</Link></nav>
    </div></footer>
  </>
}

import { useEffect, useRef } from 'react'
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
  const accountMenu = useRef<HTMLDetailsElement>(null)
  useEffect(() => {
    function dismissAccountMenu(event: PointerEvent) {
      const menu = accountMenu.current
      if (menu?.open && !event.composedPath().includes(menu)) menu.open = false
    }
    document.addEventListener('pointerdown', dismissAccountMenu, true)
    return () => document.removeEventListener('pointerdown', dismissAccountMenu, true)
  }, [])
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
        {data?.user ? <details key={key} ref={accountMenu} className="account-menu" onKeyDown={event => {
          if (event.key === 'Escape' && event.currentTarget.open) {
            event.currentTarget.open = false
            event.currentTarget.querySelector('summary')?.focus()
          }
        }}><summary>Account <span aria-hidden="true" /></summary><div className="menu">
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
    {workspace && data?.user ? <footer className="workspace-footer"><div className="wrap">
      <Link to="/">Motorlane</Link><a href="#main">Back to top ↑</a>
    </div></footer> : <footer className="marketplace-footer"><div className="wrap footer-grid">
      <div><Link className="brand" to="/"><span className="brand-mark" aria-hidden="true">M</span> Motorlane</Link>
        <p>Local car and bike rentals.</p></div>
      <nav aria-label="Explore rentals"><strong>Explore rentals</strong><Link to="/vehicles">All vehicles</Link>
        <Link to="/vehicles?type=Car">Browse cars</Link><Link to="/vehicles?type=Bike">Browse bikes</Link></nav>
      <nav aria-label="Vehicle owners"><strong>Vehicle owners</strong><Link to="/owner/fleet?edit=new">List your vehicle</Link>
        <Link to="/owner">Owner workspace</Link></nav>
    </div></footer>}
  </>
}

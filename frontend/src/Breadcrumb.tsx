import { Link } from 'react-router-dom'

export function Breadcrumb({ to, parent, current }: { to: string; parent: string; current: string }) {
  return <nav className="breadcrumb" aria-label="Breadcrumb">
    <Link to={to}>{parent}</Link><span aria-hidden="true">/</span><span aria-current="page">{current}</span>
  </nav>
}

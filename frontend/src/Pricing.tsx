import { money } from './api'

export function Price({ value, label }: { value: string | number; label?: string }) {
  return <span className="price-display"><strong>{money(value)}</strong>{label && <small>{label}</small>}</span>
}

export function PriceBreakdown({ rate, days, total, estimate = false }: {
  rate: string | null; days: number; total: string; estimate?: boolean
}) {
  return <section className="price-breakdown">
    <h3>{estimate ? 'Rental estimate' : 'Price breakdown'}</h3>
    <dl>
      {rate && <div><dt>Daily rental rate</dt><dd>{money(rate)}</dd></div>}
      <div><dt>Rental duration</dt><dd>{days} {days === 1 ? 'day' : 'days'}</dd></div>
      <div className="price-total">
        <dt>{estimate ? 'Estimated total' : 'Booking total'}<small>{rate ? `${money(rate)} × ${days} ${days === 1 ? 'day' : 'days'}` : 'Recorded rental amount'}</small></dt>
        <dd>{money(total)}</dd>
      </div>
    </dl>
  </section>
}

import type { Vehicle } from './api'

const message = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'

export function Notice({ error }: { error: unknown }) {
  return error ? <p className="error" role="alert">{message(error)}</p> : null
}
export function Busy() { return <p className="loading" role="status">Loading…</p> }
export function Photo({ vehicle }: { vehicle: Vehicle }) {
  return vehicle.vehicle_image
    ? <img className="photo" src={vehicle.vehicle_image} alt={vehicle.name} loading="lazy" />
    : <div className="photo placeholder">{vehicle.vehicle_type}</div>
}


export function Status({ value }: { value: string }) {
  return <span className="status" data-status={value}>{value}</span>
}

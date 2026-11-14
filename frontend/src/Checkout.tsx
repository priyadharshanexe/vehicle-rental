import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { api, dateLabel } from "./api";
import type { VehicleDetail } from "./api";
import { useSession, useWrite } from "./requests";
import { PriceBreakdown } from "./Pricing";
import { Busy, Notice, Photo } from "./shared";
import { Breadcrumb } from "./Breadcrumb";

export function Checkout() {
  const { id } = useParams(),
    [params] = useSearchParams(),
    navigate = useNavigate();
  const start = params.get("start_date") || "",
    end = params.get("end_date") || "";
  const session = useSession(),
    write = useWrite<{ id: number }>();
  const [accepted, setAccepted] = useState(false);
  const vehicle = useQuery({
    queryKey: ["vehicle", id],
    queryFn: () => api<VehicleDetail>(`vehicles/${id}/`),
  });
  const quote = useQuery({
    queryKey: ["checkout-quote", id, start, end],
    queryFn: () =>
      api<{ days: number; total_price: string }>(
        `vehicles/${id}/quote/?${new URLSearchParams({ start_date: start, end_date: end })}`,
      ),
    retry: false,
  });
  if (vehicle.isPending) return <Busy />;
  if (!vehicle.data) return <Notice error={vehicle.error} />;
  const v = vehicle.data;
  return (
    <>
      <Breadcrumb
        to={`/vehicles/${id}?${params}`}
        parent="Vehicle details"
        current="Review your rental"
      />
      <div className="checkout-heading">
        <span className="eyebrow">One step closer to the open road</span>
        <h1>Review your rental.</h1>
        <p>Check the details before sending your request to the owner.</p>
        <ol className="checkout-steps" aria-label="Booking progress">
          <li className="done">
            <Link to={`/vehicles/${id}?${params}`}>
              <span className="step-node" aria-hidden="true">
                ✓
              </span>
              <span>
                <strong>Choose your ride</strong>
                <small>Vehicle & dates selected</small>
              </span>
            </Link>
          </li>
          <li className="active" aria-current="step">
            <span className="step-node" aria-hidden="true">
              2
            </span>
            <span>
              <strong>Review & request</strong>
              <small>Confirm your trip details</small>
            </span>
          </li>
          <li>
            <span className="step-node" aria-hidden="true">
              3
            </span>
            <span>
              <strong>Owner confirmation</strong>
              <small>Await your host’s response</small>
            </span>
          </li>
        </ol>
      </div>
      <div className="checkout-layout">
        <div className="checkout-sections">
          <section className="panel">
            <h2>Your rental</h2>
            <div className="checkout-vehicle">
              <Photo vehicle={v} />
              <div>
                <span className="eyebrow">
                  {v.vehicle_type} · {v.fuel_type}
                </span>
                <h2>{v.name}</h2>
                <p>Listed by {v.host_name || "Vehicle owner"}</p>
              </div>
            </div>
            <div className="handoff-grid">
              <div>
                <span className="eyebrow">Pickup</span>
                <h3>{start ? dateLabel(start) : "Select a date"}</h3>
                <p>⌖ {v.location || "Arrange with owner"}</p>
              </div>
              <div>
                <span className="eyebrow">Return</span>
                <h3>{end ? dateLabel(end) : "Select a date"}</h3>
                <p>⌖ {v.location || "Arrange with owner"}</p>
              </div>
            </div>
            <Link className="button secondary" to={`/vehicles/${id}?${params}`}>
              Edit rental dates
            </Link>
          </section>
          <section className="panel">
            <span className="eyebrow">The person renting</span>
            <h2>Who’s taking the wheel?</h2>
            <p>Your contact details help the owner arrange your handoff.</p>
            <div className="fields">
              <label>
                Full name
                <input
                  name="contact_name"
                  form="rental-checkout"
                  autoComplete="name"
                  defaultValue={session.data?.user?.name}
                  maxLength={100}
                  required
                />
              </label>
              <label>
                Contact phone
                <input
                  name="contact_phone"
                  form="rental-checkout"
                  type="tel"
                  autoComplete="tel"
                  placeholder="Phone number for pickup coordination"
                  minLength={7}
                  maxLength={30}
                  required
                />
              </label>
              <label>
                Pickup notes <span className="optional">Optional</span>
                <textarea
                  name="pickup_notes"
                  form="rental-checkout"
                  placeholder="Share any handoff arrangements you would like to discuss."
                  maxLength={1000}
                />
              </label>
            </div>
          </section>
          <section className="panel">
            <h2>Pickup & rental conditions</h2>
            <p>
              {v.pickup_instructions ||
                "Arrange the exact pickup point and handoff with the owner after confirmation."}
            </p>
            <ul className="conditions">
              <li>Pickup and return dates both count as rental days.</li>
              <li>
                The owner has up to 24 hours to respond. A request is not a
                confirmed rental.
              </li>
              <li>
                Pending requests can be cancelled. Confirmed bookings can be
                cancelled before the pickup date.
              </li>
              <li>
                Insurance, deposits, and any additional arrangements must be
                confirmed with the owner. They are not included as paid extras
                here.
              </li>
            </ul>
          </section>
        </div>
        <aside className="checkout-summary panel">
          <span className="eyebrow">Clear pricing. No surprises.</span>
          <h2>Booking summary</h2>
          {quote.isPending && <Busy />}
          <Notice error={quote.error} />
          {quote.data && (
            <PriceBreakdown
              rate={v.price_per_day}
              days={quote.data.days}
              total={quote.data.total_price}
            />
          )}
          <div className="payment-note">
            <strong>No payment collected now</strong>
            <p>
              This sends a rental request. Payment collection is not available
              on Motorlane yet.
            </p>
          </div>
          <form
            id="rental-checkout"
            className="fields"
            onSubmit={(event) => {
              event.preventDefault();
              if (!accepted || !quote.data || write.isPending) return;
              write.mutate(
                {
                  path: "bookings/",
                  body: {
                    vehicle_id: v.id,
                    start_date: start,
                    end_date: end,
                    checkout: true,
                    accepted_conditions: accepted,
                    ...Object.fromEntries(new FormData(event.currentTarget)),
                  },
                },
                { onSuccess: (result) => navigate(`/bookings/${result.id}`) },
              );
            }}
          >
            <label className="check-label">
              <input
                type="checkbox"
                checked={accepted}
                onChange={(event) => setAccepted(event.target.checked)}
                required
              />
              <span>
                I have reviewed the dates, total, and rental conditions above.
              </span>
            </label>
            <Notice error={write.error} />
            <button disabled={!accepted || !quote.data || write.isPending}>
              {write.isPending ? "Sending request…" : "Confirm & send request"}
            </button>
          </form>
          <p className="fine-print">
            Availability and the price are checked again when your request is
            submitted.
          </p>
        </aside>
      </div>
    </>
  );
}

import { useQuery } from "@tanstack/react-query";
import { useState, useRef, useEffect } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { api, queryString } from "./api";
import type { Vehicle, VehicleDetail } from "./api";
import { Busy, Notice, Photo } from "./shared";
import { formData, useSession } from "./requests";
import { Price, PriceBreakdown } from "./Pricing";
import { RentalCalendar } from "./RentalCalendar";
import { FavoriteButton, Rating } from "./Favorites";
import { Breadcrumb } from "./Breadcrumb";
import { overlapsUnavailableDates } from "./marketplaceData";
import heroImage from "./assets/studio-splendor.png";

type CatalogResult = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Vehicle[];
};
function Search({
  params,
  compact = false,
}: {
  params?: URLSearchParams;
  compact?: boolean;
}) {
  const navigate = useNavigate();
  return (
    <form
      className="filters"
      key={params?.toString()}
      onSubmit={(event) =>
        navigate(`/vehicles?${queryString(formData(event))}`)
      }
    >
      <label>
        Location
        <input
          name="location"
          placeholder="Where are you going?"
          defaultValue={params?.get("location") ?? ""}
        />
      </label>
      <label>
        Pickup
        <input
          type="date"
          name="start_date"
          defaultValue={params?.get("start_date") ?? ""}
        />
      </label>
      <label>
        Return
        <input
          type="date"
          name="end_date"
          defaultValue={params?.get("end_date") ?? ""}
        />
      </label>
      {!compact && (
        <label>
          Vehicle name
          <input
            name="q"
            placeholder="Search a model"
            defaultValue={params?.get("q") ?? ""}
          />
        </label>
      )}
      <label>
        Vehicle type
        <select name="type" defaultValue={params?.get("type") ?? ""}>
          <option value="">Cars & bikes</option>
          <option>Car</option>
          <option>Bike</option>
        </select>
      </label>
      {!compact && (
        <label>
          Fuel
          <input name="fuel" defaultValue={params?.get("fuel") ?? ""} />
        </label>
      )}
      <button>Search rides ↗</button>
    </form>
  );
}
export function Home() {
  const query = useQuery({
    queryKey: ["vehicles", "featured"],
    queryFn: () => api<CatalogResult>("vehicles/"),
  });
  const [category, setCategory] = useState("All");
  const vehicles = (query.data?.results ?? [])
    .filter(
      (v, index, rows) =>
        rows.findIndex((other) => other.name === v.name) === index,
    )
    .filter((v) => category === "All" || v.vehicle_type === category);
  return (
    <>
      <section className="hero studio-hero">
        <div className="hero-orbit" aria-hidden="true" />
        <div className="hero-ridge" aria-hidden="true" />
        <div className="hero-copy">
          <span className="eyebrow">GOOD ROADS. GREAT MEMORIES.</span>
          <h1>
            Your next chapter.
            <br />
            <em>A better ride.</em>
          </h1>
          <p>
            From everyday errands to weekend escapes. Find a car or bike that
            feels like you.
          </p>
          <Link to="/vehicles" className="button hero-explore">
            Explore the collection ↗
          </Link>
        </div>
        <div className="hero-stage">
          <img
            className="hero-vehicle"
            src={heroImage}
            alt="Black Hero Honda Splendor motorcycle, realistic studio render"
          />
          <span className="hero-caption">THE FREEDOM TO GO YOUR WAY</span>
        </div>
        <div className="hero-search">
          <div className="search-caption">
            <strong>Where will the road take you?</strong>
            <span>Find your car or bike</span>
          </div>
          <Search compact />
        </div>
      </section>
      <div className="brand-strip">
        <span>Made for every kind of journey</span>
        <strong>City drives</strong>
        <span>✦</span>
        <strong>Weekend escapes</strong>
        <span>✦</span>
        <strong>Two-wheel freedom</strong>
      </div>
      <section className="collection">
        <div className="section-head">
          <div>
            <span className="eyebrow">THE COLLECTION</span>
            <h2>Find your kind of ride.</h2>
          </div>
          <Link className="button secondary" to="/vehicles">
            Explore all vehicles ↗
          </Link>
        </div>
        <div
          className="collection-tabs"
          role="group"
          aria-label="Vehicle category"
        >
          {["All", "Car", "Bike"].map((type) => (
            <button
              key={type}
              aria-pressed={category === type}
              onClick={() => setCategory(type)}
            >
              {type === "All" ? "All rides" : type + "s"}
            </button>
          ))}
        </div>
        {query.isPending && <Busy />}
        <Notice error={query.error} />
        <div className="cards home-cards">
          {vehicles.slice(0, 6).map((vehicle) => (
            <Listing key={vehicle.id} vehicle={vehicle} />
          ))}
        </div>
        {query.data && !vehicles.length && (
          <p className="empty">New listings are on their way.</p>
        )}
      </section>
      <section className="how">
        <span className="eyebrow">LESS PLANNING. MORE GOING.</span>
        <h2>Your journey in three steps.</h2>
        <ol>
          <li>
            <strong>Find your perfect ride</strong>
            <p>
              Explore cars and bikes from local owners. Save your favorites for
              later.
            </p>
          </li>
          <li>
            <strong>Make it your trip</strong>
            <p>
              Choose your dates and review the rental summary before sending a
              request.
            </p>
          </li>
          <li>
            <strong>Get out there</strong>
            <p>
              Once the owner confirms, arrange your pickup and track your trip
              in your dashboard.
            </p>
          </li>
        </ol>
      </section>
      <section className="owner-callout">
        <div>
          <span className="eyebrow">YOUR VEHICLE. NEW POSSIBILITIES.</span>
          <h2>Let your vehicle go places.</h2>
          <p>
            Put your parked vehicle to work. You set the price and decide which
            requests to accept.
          </p>
        </div>
        <Link className="button" to="/owner/fleet?edit=new">
          Become a host ↗
        </Link>
      </section>
    </>
  );
}
export function Listing({
  vehicle,
  params = "",
}: {
  vehicle: Vehicle;
  params?: string;
}) {
  const [preview, setPreview] = useState(false);
  const url = `/vehicles/${vehicle.id}${params ? "?" + params : ""}`;
  return (
    <article
      className="listing ride-card"
      data-vehicle-type={vehicle.vehicle_type}
    >
      <div className="ride-media">
        <Link to={url} aria-label={`View ${vehicle.name}`}>
          <Photo vehicle={vehicle} />
        </Link>
        <span className="ride-type">{vehicle.vehicle_type}</span>
        <FavoriteButton vehicle={vehicle} />
        <button className="quick-preview" onClick={() => setPreview(true)}>
          Quick view <span aria-hidden="true">↗</span>
        </button>
      </div>
      <div className="listing-body">
        <div className="ride-title">
          <h3>
            <Link to={url}>{vehicle.name}</Link>
          </h3>
          <Rating vehicle={vehicle} />
        </div>
        <p className="card-location">
          <span className="location-pin" aria-hidden="true" />
          {vehicle.location || "Location on request"}
        </p>
        <div className="card-specs">
          <span>{vehicle.fuel_type}</span>
          {vehicle.transmission && <span>{vehicle.transmission}</span>}
          {vehicle.seats && <span>{vehicle.seats} seats</span>}
        </div>
        <div className="listing-bottom">
          <Price value={vehicle.price_per_day} label="/ day" />
          <Link className="ride-book" to={url}>
            Explore ride <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </div>
      {preview && (
        <VehiclePreview
          vehicle={vehicle}
          url={url}
          onClose={() => setPreview(false)}
        />
      )}
    </article>
  );
}
function VehiclePreview({
  vehicle,
  url,
  onClose,
}: {
  vehicle: Vehicle;
  url: string;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const node = dialog.current;
    node?.showModal();
    return () => node?.close();
  }, []);
  const details = useQuery({
    queryKey: ["vehicle", String(vehicle.id)],
    queryFn: () => api<VehicleDetail>(`vehicles/${vehicle.id}/`),
  });
  return (
    <dialog
      className="vehicle-preview"
      ref={dialog}
      aria-labelledby={`preview-${vehicle.id}`}
      onCancel={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          const r = event.currentTarget.getBoundingClientRect();
          if (
            event.clientX < r.left ||
            event.clientX > r.right ||
            event.clientY < r.top ||
            event.clientY > r.bottom
          )
            onClose();
        }
      }}
    >
      <button
        className="preview-close"
        aria-label="Close vehicle preview"
        onClick={onClose}
      >
        ×
      </button>
      <Photo vehicle={vehicle} />
      <div className="preview-copy">
        <span className="eyebrow">TAKE A CLOSER LOOK</span>
        <h2 id={`preview-${vehicle.id}`}>{vehicle.name}</h2>
        <p>
          {vehicle.location} · {vehicle.vehicle_type} · {vehicle.fuel_type}
        </p>
        <Rating vehicle={vehicle} />
        <p>
          {details.data?.description ||
            "Choose your dates on the listing to see availability and review your rental."}
        </p>
        <Notice error={details.error} />
        <div className="preview-footer">
          <Price value={vehicle.price_per_day} label="/ day" />
          <Link className="button" to={url}>
            View details & dates →
          </Link>
        </div>
      </div>
    </dialog>
  );
}
export function Catalog() {
  const [params, setParams] = useSearchParams();
  const query = useQuery({
    queryKey: ["vehicles", params.toString()],
    queryFn: () => api<CatalogResult>(`vehicles/?${params}`),
  });
  function page(delta: number) {
    const next = new URLSearchParams(params);
    next.set("page", String(Number(params.get("page") || 1) + delta));
    setParams(next);
  }
  return (
    <>
      <div className="catalog-heading">
        <span className="eyebrow">A RIDE FOR EVERY REASON</span>
        <h1>
          {params.get("type") === "Car"
            ? "Discover your next car."
            : params.get("type") === "Bike"
              ? "Life on two wheels."
              : "Where do you want to go?"}
        </h1>
        <p>Local owners. Distinctive rides. Your next journey starts here.</p>
      </div>
      <div className="catalog">
        <aside>
          <details className="mobile-filters">
            <summary>Refine your search</summary>
            <Search params={params} />
            <Link to="/vehicles">Reset filters</Link>
          </details>
          <div className="desktop-filters">
            <span className="eyebrow">MAKE IT YOURS</span>
            <h2>Refine your search</h2>
            <Search params={params} />
            <Link className="button secondary" to="/vehicles">
              Reset filters
            </Link>
          </div>
        </aside>
        <section>
          {query.isPending && <Busy />}
          <Notice error={query.error} />
          <div className="cards">
            {query.data?.results.map((vehicle) => (
              <Listing
                key={vehicle.id}
                vehicle={vehicle}
                params={params.toString()}
              />
            ))}
          </div>
          {query.data?.count === 0 && (
            <div className="empty panel">
              <h2>No rides for these filters.</h2>
              <p>Try a different location or date range.</p>
              <Link className="button" to="/vehicles">
                Explore all rides
              </Link>
            </div>
          )}
          {(query.data?.previous || query.data?.next) && (
            <nav className="actions" aria-label="Catalog pages">
              {query.data.previous && (
                <button onClick={() => page(-1)}>Previous</button>
              )}
              {query.data.next && <button onClick={() => page(1)}>Next</button>}
            </nav>
          )}
        </section>
      </div>
    </>
  );
}
export function VehiclePage() {
  const { id } = useParams(),
    [params] = useSearchParams();
  return <VehicleReservation key={id} id={id} params={params} />;
}
function VehicleReservation({
  id,
  params,
}: {
  id: string | undefined;
  params: URLSearchParams;
}) {
  const [start, setStart] = useState(params.get("start_date") || ""),
    [end, setEnd] = useState(params.get("end_date") || "");
  const query = useQuery({
    queryKey: ["vehicle", id],
    queryFn: () => api<VehicleDetail>(`vehicles/${id}/`),
  });
  const blocked =
    overlapsUnavailableDates(query.data?.unavailable || [], start, end) &&
    start <= end;
  const valid = Boolean(start && end && start <= end && !blocked);
  const qp = new URLSearchParams({ start_date: start, end_date: end });
  const quote = useQuery({
    queryKey: ["quote", id, start, end],
    enabled: valid,
    queryFn: ({ signal }) =>
      api<{ days: number; total_price: string }>(
        `vehicles/${id}/quote/?${qp}`,
        { signal },
      ),
    retry: false,
  });
  const navigate = useNavigate(),
    session = useSession();
  if (query.isPending) return <Busy />;
  if (!query.data) return <Notice error={query.error} />;
  const v = query.data,
    ready = valid && Boolean(quote.data) && !quote.isError;
  return (
    <>
      <Breadcrumb
        to={`/vehicles?${params}`}
        parent="Explore vehicles"
        current={v.name}
      />
      <div className="detail modern-detail">
        <section className="vehicle-intro">
          <div className="listing-host">
            <span className="listing-host-avatar">
              {v.host_name?.[0] || "M"}
            </span>
            <div>
              <span>Your local host</span>
              <strong>{v.host_name || "Vehicle owner"}</strong>
            </div>
          </div>
          <div className="page-heading">
            <h1>{v.name}</h1>
            <p className="vehicle-location">
              <span className="location-pin" aria-hidden="true" />
              {v.location || "Location on request"}
            </p>
          </div>
          <div className="detail-photo">
            <Photo vehicle={v} />
            <FavoriteButton vehicle={v} />
          </div>
          <div className="detail-rating">
            <Rating vehicle={v} />
            <a href="#vehicle-reviews">Read reviews</a>
          </div>
        </section>
        <aside className="panel reservation">
          <span className="eyebrow">MAKE THIS RIDE YOURS</span>
          <h2>
            <Price value={v.price_per_day} label="/ day" />
          </h2>
          <p>Choose your trip dates. Review everything before you request.</p>
          <form
            className="fields"
            onSubmit={(event) => {
              event.preventDefault();
              if (!ready) return;
              const next = `/checkout/${v.id}?${qp}`;
              navigate(
                session.data?.user
                  ? next
                  : `/sign-in?next=${encodeURIComponent(next)}`,
              );
            }}
          >
            <div className="reservation-dates">
              <label>
                Pickup
                <input
                  type="date"
                  required
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                />
              </label>
              <label>
                Return
                <input
                  type="date"
                  required
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                />
              </label>
            </div>
            <RentalCalendar
              start={start}
              end={end}
              unavailable={v.unavailable}
              onSelect={(a, b) => {
                setStart(a);
                setEnd(b);
              }}
            />
            <div aria-live="polite">
              {blocked && (
                <div className="quote quote-unavailable">
                  <strong>These dates are unavailable</strong>
                  <p>Choose another date range for this vehicle.</p>
                </div>
              )}
              {start && end && end < start && (
                <p className="error">Return must be on or after pickup.</p>
              )}
              {ready && quote.data && (
                <>
                  <div className="quote quote-available">
                    <strong>Available for your dates</strong>
                  </div>
                  <PriceBreakdown
                    rate={v.price_per_day}
                    days={quote.data.days}
                    total={quote.data.total_price}
                    estimate
                  />
                </>
              )}
              <Notice error={quote.error} />
            </div>
            <button disabled={!ready}>
              {blocked
                ? "Choose other dates"
                : !start || !end
                  ? "Select your trip dates"
                  : quote.isFetching
                    ? "Checking availability…"
                    : "Continue to checkout →"}
            </button>
            <p className="fine-print">
              No payment now · Owner confirmation required
            </p>
          </form>
        </aside>
        <section className="vehicle-information">
          <div className="vehicle-specs">
            <span className="eyebrow">THE DETAILS THAT MATTER</span>
            <h2>Meet your ride.</h2>
            <p>
              {v.description ||
                `Discover ${v.location || "your destination"} with this ${v.name}. Check the specifications below and select dates to plan your rental.`}
            </p>
            <dl>
              {[
                ["Category", v.vehicle_type],
                ["Fuel", v.fuel_type],
                ["Transmission", v.transmission || "Not provided"],
                ["Seats", v.seats || "Not provided"],
                ["Model year", v.model_year || "Not provided"],
                ["Pickup location", v.location || "Arrange with host"],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </div>
          <section className="panel">
            <h2>Pickup & handoff</h2>
            <p>
              {v.pickup_instructions ||
                "Arrange the exact pickup point with the owner after confirmation."}
            </p>
            <p>
              Both pickup and return dates count towards your rental. Review the
              full summary at checkout.
            </p>
          </section>
          <section className="panel" id="vehicle-reviews">
            <span className="eyebrow">REAL RENTALS. REAL EXPERIENCES.</span>
            <h2>From the driver’s seat.</h2>
            <Rating vehicle={v} />
            {v.reviews.length ? (
              v.reviews.map((review) => (
                <article className="review" key={review.id}>
                  <span
                    className="review-stars"
                    aria-label={`${review.rating} out of 5 stars`}
                  >
                    {"★".repeat(review.rating)}
                    {"☆".repeat(5 - review.rating)}
                  </span>
                  <p>{review.comment}</p>
                  <small>Verified completed rental</small>
                </article>
              ))
            ) : (
              <p>
                No reviews yet. Customers can review this vehicle after
                completing their rental.
              </p>
            )}
          </section>
        </section>
      </div>
    </>
  );
}

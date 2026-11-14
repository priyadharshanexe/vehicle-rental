import { MetricIcon } from "./MetricIcon";
import { useState } from "react";
import { Price } from "./Pricing";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, dateLabel } from "./api";
import type { Booking, BookingValue, FleetVehicle } from "./api";
import { Busy, Notice, Photo, Status } from "./shared";
import { useSession } from "./requests";

export function Dashboard({ owner = false }: { owner?: boolean }) {
  const [fleetSearch, setFleetSearch] = useState("");
  const session = useSession();
  const bookings = useQuery({
    queryKey: [owner ? "owner-bookings" : "bookings"],
    queryFn: () => api<Booking[]>(owner ? "owner/bookings/" : "bookings/"),
  });
  const fleet = useQuery({
    queryKey: ["fleet"],
    queryFn: () => api<FleetVehicle[]>("owner/fleet/"),
    enabled: owner,
  });
  const values = useQuery({
    queryKey: ["values", ""],
    queryFn: () => api<BookingValue[]>("owner/value/"),
    enabled: owner,
  });
  const rows = bookings.data ?? [];
  const pending = rows.filter((row) => row.status === "Pending");
  const confirmed = rows.filter((row) => row.status === "Confirmed");
  const active = rows.filter((row) => row.status === "In progress");
  const returned = rows.filter((row) => row.status === "Returned");
  const upcoming = [...pending, ...confirmed].sort((a, b) =>
    a.start_date.localeCompare(b.start_date),
  );
  const recent = [...rows].sort((a, b) => b.id - a.id).slice(0, 4);
  const listings = fleet.data?.filter((row) => !row.archived_at);
  const nextTrip = upcoming[0];
  const spent = returned.reduce((sum, row) => sum + Number(row.total_price), 0);
  const metrics: [string, string | number | React.JSX.Element | undefined][] =
    owner
      ? [
          ["Fleet listings", listings?.length],
          ["Published", listings?.filter((row) => row.is_available).length],
          ["Pending requests", bookings.data && pending.length],
          ["Active rentals", bookings.data && active.length],
          [
            "Overdue returns",
            bookings.data && active.filter((row) => row.overdue).length,
          ],
          [
            "Completed booking value",
            values.data && (
              <Price
                key="completed-value"
                value={values.data.reduce(
                  (sum, row) => sum + Number(row.value),
                  0,
                )}
              />
            ),
          ],
        ]
      : [
          ["Upcoming", bookings.data && upcoming.length],
          ["Active rentals", bookings.data && active.length],
          ["Completed", bookings.data && returned.length],
          [
            "Completed rental value",
            bookings.data && <Price key="rental-value" value={spent} />,
          ],
        ];
  return (
    <>
      <div className="page-heading section-head">
        <div>
          <span className="eyebrow">
            {owner ? "HOST COMMAND CENTER" : "YOUR JOURNEY, AT A GLANCE"}
          </span>
          <h1>
            {owner
              ? "Fleet overview"
              : `Welcome, ${session.data?.user?.name ?? "renter"}`}
          </h1>
          <p>
            {owner
              ? "Review your listings, requests, and upcoming handoffs."
              : "See what’s coming up and manage your rentals."}
          </p>
        </div>
        <Link
          className="button"
          to={owner ? "/owner/fleet?edit=new" : "/vehicles"}
        >
          {owner ? "List a vehicle" : "Browse vehicles"}
        </Link>
      </div>
      {!owner && (
        <section className="next-trip">
          <div>
            <span className="eyebrow">
              {nextTrip ? "NEXT ON YOUR CALENDAR" : "THE ROAD IS CALLING"}
            </span>
            <h2>
              {nextTrip ? nextTrip.vehicle.name : "Where will you go next?"}
            </h2>
            <p>
              {nextTrip
                ? `${dateLabel(nextTrip.start_date)} — ${dateLabel(nextTrip.end_date)} · ${nextTrip.vehicle.location || "Local pickup"}`
                : "Explore local rides and build a collection of your favorites."}
            </p>
            <Link
              className="button"
              to={nextTrip ? `/bookings/${nextTrip.id}` : "/vehicles"}
            >
              {nextTrip ? "Manage your trip" : "Find your next ride"} →
            </Link>
          </div>
          {nextTrip && <Photo vehicle={nextTrip.vehicle} />}
        </section>
      )}
      <div className="metrics dashboard-metrics">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <MetricIcon label={label} />
            {typeof value === "object" ? (
              value
            ) : (
              <strong>{value ?? "—"}</strong>
            )}
          </div>
        ))}
      </div>
      {bookings.isPending && <Busy />}
      <Notice error={bookings.error ?? fleet.error ?? values.error} />
      {owner ? (
        <section className="panel fleet-overview">
          <div className="section-head">
            <h2>Fleet overview</h2>
            <Link to="/owner/fleet">Manage fleet</Link>
          </div>
          <label className="fleet-search">
            Search your fleet
            <input
              placeholder="Find a vehicle by name"
              value={fleetSearch}
              onChange={(event) => setFleetSearch(event.target.value)}
            />
          </label>
          <div className="fleet-preview">
            {listings
              ?.filter((v) =>
                v.name.toLowerCase().includes(fleetSearch.toLowerCase()),
              )
              .slice(0, 6)
              .map((vehicle) => (
                <article key={vehicle.id}>
                  <Photo vehicle={vehicle} />
                  <div>
                    <h3>{vehicle.name}</h3>
                    <p>{vehicle.location}</p>
                    <Price value={vehicle.price_per_day} label="/ day" />
                    <Status
                      value={vehicle.is_available ? "Published" : "Unpublished"}
                    />
                  </div>
                </article>
              ))}
          </div>
          {listings?.length === 0 && <p>No fleet listings yet.</p>}
        </section>
      ) : (
        <section className="panel current-rentals">
          <h2>Current rentals</h2>
          <BookingRows rows={active} />
        </section>
      )}
      <div className="dashboard-grid">
        <section className="panel">
          <div className="section-head">
            <h2>{owner ? "Recent requests" : "Recent bookings"}</h2>
            <Link to={owner ? "/owner/requests" : "/bookings"}>View all →</Link>
          </div>
          <BookingRows
            owner={owner}
            rows={owner ? pending.slice(-4).reverse() : recent}
          />
        </section>
        <section className="panel">
          <h2>{owner ? "Pickup and return schedule" : "Upcoming bookings"}</h2>
          {owner ? (
            <BookingRows owner rows={[...active, ...confirmed].slice(0, 4)} />
          ) : (
            <BookingRows rows={upcoming.slice(0, 4)} />
          )}
        </section>
      </div>
      <div className="quick-links">
        {(owner
          ? [
              ["/owner/fleet", "Manage fleet"],
              ["/owner/maintenance", "Schedule maintenance"],
              ["/owner/value", "View booking value"],
            ]
          : [
              ["/bookings", "Manage bookings"],
              ["/favorites", "Your saved collection"],
              ["/vehicles", "Find a vehicle"],
            ]
        ).map(([url, label]) => (
          <Link key={url} to={url}>
            {label} →
          </Link>
        ))}
      </div>
    </>
  );
}

function BookingRows({
  rows,
  owner = false,
}: {
  rows: Booking[];
  owner?: boolean;
}) {
  if (!rows.length) return <p className="empty">No bookings to show here.</p>;
  return (
    <ul className="dashboard-list">
      {rows.map((row) => (
        <li key={row.id}>
          <Photo vehicle={row.vehicle} />
          <div>
            <Link to={owner ? "/owner/requests" : `/bookings/${row.id}`}>
              {row.vehicle.name}
            </Link>
            <p>
              {row.status === "In progress" ? "Return" : "Pickup"} ·{" "}
              {dateLabel(
                row.status === "In progress" ? row.end_date : row.start_date,
              )}
            </p>
          </div>
          <div className="dashboard-row-value">
            <Status value={row.status} />
            <Price value={row.total_price} />
          </div>
        </li>
      ))}
    </ul>
  );
}

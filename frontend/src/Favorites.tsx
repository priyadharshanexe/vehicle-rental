import { useQuery } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api } from "./api";
import type { Vehicle } from "./api";
import { useSession, useWrite } from "./requests";
import { Listing } from "./Marketplace";
import { Busy, Notice } from "./shared";

function useFavorites() {
  const session = useSession();
  return useQuery({
    queryKey: ["favorites", session.data?.user?.id],
    queryFn: () => api<Vehicle[]>("favorites/"),
    enabled: Boolean(session.data?.user),
  });
}
export function FavoriteButton({ vehicle }: { vehicle: Vehicle }) {
  const session = useSession(),
    saved = useFavorites(),
    write = useWrite();
  const navigate = useNavigate(),
    location = useLocation();
  const selected = saved.data?.some((item) => item.id === vehicle.id) ?? false;
  return (
    <div className="favorite-control">
      <button
        className="favorite-button"
        aria-label={`${selected ? "Remove" : "Save"} ${vehicle.name}${selected ? " from" : " to"} favorites`}
        aria-pressed={selected}
        disabled={write.isPending}
        onClick={() => {
          if (!session.data?.user) {
            navigate(
              `/sign-in?next=${encodeURIComponent(location.pathname + location.search)}`,
            );
            return;
          }
          write.mutate({
            path: `favorites/${vehicle.id}/`,
            method: selected ? "DELETE" : "POST",
          });
        }}
      >
        <svg
          viewBox="0 0 24 24"
          fill={selected ? "currentColor" : "none"}
          stroke="currentColor"
          strokeWidth="1.7"
          aria-hidden="true"
        >
          <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z" />
        </svg>
      </button>
      <Notice error={write.error} />
    </div>
  );
}
export function Rating({ vehicle }: { vehicle: Vehicle }) {
  return (
    <span className="vehicle-rating">
      <span aria-hidden="true">★</span>{" "}
      {vehicle.rating
        ? `${Number(vehicle.rating).toFixed(1)} · ${vehicle.review_count} review${vehicle.review_count === 1 ? "" : "s"}`
        : "New listing"}
    </span>
  );
}
export function Favorites() {
  const query = useFavorites();
  return (
    <>
      <div className="page-heading">
        <span className="eyebrow">Your collection</span>
        <h1>Saved for your next trip.</h1>
        <p>
          Keep the vehicles you love together. Choose dates when you’re ready to
          book.
        </p>
      </div>
      {query.isPending && <Busy />}
      <Notice error={query.error} />
      <div className="cards">
        {query.data?.map((vehicle) => (
          <Listing key={vehicle.id} vehicle={vehicle} />
        ))}
      </div>
      {query.data?.length === 0 && (
        <section className="panel empty">
          <h2>Your next favorite is out there.</h2>
          <p>Tap the heart on any vehicle to save it here.</p>
          <Link className="button" to="/vehicles">
            Explore vehicles
          </Link>
        </section>
      )}
    </>
  );
}

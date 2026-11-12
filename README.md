# Vehicle Rental System

A Django and MySQL marketplace where customers can browse cars and bikes and request rentals from vehicle owners.

## What you can do

- Find cars and bikes by location, dates, type, and fuel.
- Request a rental, review its quote, and track pickup and return.
- Manage listings, requests, and maintenance as a vehicle owner.
- Review a vehicle after completing a rental.

## Run locally

1. Create a Python virtual environment and install dependencies with `python -m pip install -r requirements.txt`.
2. Create a MySQL database and grant a dedicated user access.
3. Copy `.env.example` to `.env` and fill in your local settings.
4. Run `python manage.py migrate` and `python manage.py runserver`.
5. Open http://127.0.0.1:8000/.

Run the tests with `python manage.py test` using a local MySQL user with permission to create a test database.

For a disposable local MySQL server, set `MYSQL_HOST=127.0.0.1`,
`MYSQL_PORT=33316`, and a local `MYSQL_PASSWORD` in `.env`, then run
`docker compose up -d db`. On first startup, the database initializes
the application user and grants it access to Django's test database.

## Try the local demo

With `DJANGO_DEBUG=1`, set `RENTAL_DEMO_PASSWORD` to a local password of at
least 12 characters and run `python manage.py seed_demo`. The command creates
`renter@rental-demo.example`, `owner@rental-demo.example`, and listings in Madurai.

1. Sign in as the renter, search for Madurai, and request a vehicle for today.
2. Search for the same vehicle and dates again to see availability update.
3. Sign in as the owner. In **Rental requests**, approve the request, then use
   **Pickups** and **Returns** to complete the rental.
4. Sign in as the renter to download the booking summary and leave a review.

## Booking rules

Rates apply to inclusive calendar days. A pending request holds its dates for
up to 24 hours. Confirmed bookings can be cancelled before the pickup date.
MySQL row locks serialize reservation checks by renter and vehicle. The test
suite exercises competing requests on separate database connections.

## Deployment settings

Run the Django WSGI application behind an HTTPS reverse proxy. Set
`DJANGO_DEBUG=0`, provide a unique signing key and database credentials,
and set `DJANGO_ALLOWED_HOSTS` to the public host names. Use
`DJANGO_TRUST_HTTPS_PROXY=1` only when the proxy overwrites the incoming
`X-Forwarded-Proto` header. Run migrations and `python manage.py collectstatic`;
serve the collected static directory and persistent vehicle uploads separately.
Configure SMTP for email confirmation and password reset.

## License

[MIT](LICENSE)

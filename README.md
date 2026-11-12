# Vehicle Rental System

A Django and MySQL marketplace where customers can browse cars and bikes and request rentals from vehicle owners.

## What you can do

- Find vehicles by name, type, fuel, and location.
- Request a rental and track its status.
- List vehicles and manage incoming requests as an owner.

## Run locally

1. Create a Python virtual environment and install dependencies with `python -m pip install -r requirements.txt`.
2. Create a MySQL database and grant a dedicated user access.
3. Set the variables in `.env.example` for your local environment.
4. Run `python manage.py migrate` and `python manage.py runserver`.
5. Open http://127.0.0.1:8000/.

Run the tests with `python manage.py test` using a local MySQL user with permission to create a test database.

## License

[MIT](LICENSE)

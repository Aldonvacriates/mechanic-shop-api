# Mechanic Shop API

A Flask REST API for running a mechanic shop: customers, vehicles, mechanics,
service tickets and parts inventory, with role-scoped JWT auth for customers
and mechanics.

Built as a back-end project in the Coding Temple program. It runs locally
against MySQL; there is no hosted deployment.

## Features

- CRUD for customers, vehicles, mechanics, service tickets and inventory parts
- Two JWT roles (customer and mechanic) signed with python-jose; using the
  wrong role's token returns `403`, a missing, expired or invalid token
  returns `401`
- Passwords stored as salted hashes (`werkzeug.security`)
- Rate limiting with Flask-Limiter: 200 requests/hour per client IP by default,
  10/minute on customer login, 5/minute on customer sign-up
- Cached, paginated customer list (Flask-Caching, 60 seconds, one cache entry
  per `page`/`per_page` combination)
- Bulk add/remove of mechanics on a ticket in one request
- Mechanics ranked by number of tickets worked
- Parts attached to tickets through a junction table that carries `quantity`
- Postman collection with 31 requests across all five resources, with login
  requests that save tokens automatically

## Tech stack

Python, Flask 3, Flask-SQLAlchemy / SQLAlchemy 2, Flask-Marshmallow /
Marshmallow, Flask-Limiter, Flask-Caching, python-jose, python-dotenv, MySQL
(`mysql-connector-python`).

## How it works

- **App factory and blueprints.** `app/__init__.py` builds the app with
  `create_app(config_name)`, binds the extensions from `app/extensions.py`
  (`db`, `ma`, `limiter`, `cache`) and registers one blueprint per resource.
  Each blueprint under `app/blueprints/<resource>/` has its own `routes.py`
  and Marshmallow `schemas.py`, mounted at `/customers`, `/vehicles`,
  `/mechanics`, `/service-tickets` and `/inventory`.
- **Role-scoped tokens.** `app/auth.py` has one `_encode` / `_verify` pair.
  Tokens carry `sub` (the user id), a `role` claim and a 1-hour expiry.
  `@token_required` accepts only `role=customer` and `@mechanic_token_required`
  only `role=mechanic`; both pass the authenticated id into the route, so
  customer routes such as `PUT /customers/` act on the caller and never take
  an id from the URL.
- **Relationship rules in the models.** `app/models.py` uses association
  objects (`TicketMechanic` with `role` and `hours_worked`,
  `ServiceTicketInventory` with `quantity`) instead of bare join tables, and
  cascade deletes so a removed customer takes their vehicles and tickets with
  them. Ticket creation checks that the vehicle belongs to the customer.
- **Config from the environment.** `config.py` reads `DATABASE_URL` and
  `SECRET_KEY` (loading a local `.env` via python-dotenv). Only
  `DevelopmentConfig` has a fallback `SECRET_KEY`; `create_app` raises a
  `RuntimeError` naming any missing variable, so `ProductionConfig` refuses to
  start without a real key.

## Getting started

### Prerequisites

- Python 3 (the pinned dependencies install on 3.12)
- A running MySQL server

### Install

```powershell
git clone https://github.com/Aldonvacriates/mechanic-shop-api.git
cd mechanic-shop-api
python -m venv venv
.\venv\Scripts\Activate.ps1      # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create the database:

```sql
CREATE DATABASE mechanic_shop_api_db;
```

### Environment variables

Copy `.env.example` to `.env` (git-ignored) and fill in your values:

| Variable       | Required                     | Purpose                                                                 |
| -------------- | ---------------------------- | ----------------------------------------------------------------------- |
| `DATABASE_URL` | Yes                          | SQLAlchemy URI, e.g. `mysql+mysqlconnector://user:password@localhost/mechanic_shop_api_db` |
| `SECRET_KEY`   | Yes, except in development   | Signs and verifies JWTs. `DevelopmentConfig` falls back to an insecure dev key. |

### Run

```powershell
python app.py
```

The server starts at `http://127.0.0.1:5000` using `DevelopmentConfig`.
Tables are created on startup with `db.create_all()` (there are no
migrations). There is no `/` route; start at `/customers/`, `/mechanics/`,
`/vehicles/`, `/service-tickets/` or `/inventory/`.

To use the production settings, build the app with
`create_app("ProductionConfig")` from your WSGI entry point; it requires both
environment variables.

### Tests

There is no automated test suite yet. The Postman collection below is the way
to exercise the API end to end.

## Postman collection

`Mechanic Shop API.postman_collection.json` is in the repo root. Import it into
Postman; it defines `{{base_url}}` (default `http://127.0.0.1:5000`),
`{{customer_token}}` and `{{mechanic_token}}` as collection variables.

1. Create a customer and a mechanic, each with a `password` (the **Create
   Customer** and **Create Mechanic** requests).
2. Run the **Auth** folder. The login requests save the returned tokens into
   `{{customer_token}}` and `{{mechanic_token}}`.
3. Protected requests already send `Authorization: Bearer {{customer_token}}`
   or `Bearer {{mechanic_token}}`.

The collection does not yet include the plain `PUT` and `DELETE
/service-tickets/<id>` routes.

## Authentication

1. `POST /customers/` or `POST /mechanics/` with a `password` field.
2. `POST /customers/login` or `POST /mechanics/login` with `email` and
   `password`. The response contains a `token`.
3. Send it on protected routes:

```text
Authorization: Bearer <token>
```

## Endpoints

### Auth

- `POST /customers/login` - returns a customer JWT (rate limited 10/min)
- `POST /mechanics/login` - returns a mechanic JWT

### Customers

- `POST /customers/` - create (rate limited 5/min; accepts `password`)
- `GET /customers/?page=<n>&per_page=<n>` - paginated list (cached 60s)
- `GET /customers/<int:customer_id>`
- `GET /customers/my-tickets` - **customer token**; tickets for the logged-in customer
- `PUT /customers/` - **customer token**; updates the authenticated customer
- `DELETE /customers/` - **customer token**; deletes the authenticated customer

### Vehicles

- `POST /vehicles/`
- `GET /vehicles/`
- `GET /vehicles/<int:vehicle_id>`
- `PUT /vehicles/<int:vehicle_id>`
- `DELETE /vehicles/<int:vehicle_id>`

### Mechanics

- `POST /mechanics/` - create (accepts `password`)
- `GET /mechanics/`
- `GET /mechanics/top` - mechanics ranked by tickets worked (busiest first)
- `GET /mechanics/<int:id>`
- `PUT /mechanics/<int:id>`
- `DELETE /mechanics/<int:id>`

### Service tickets

- `POST /service-tickets/`
- `GET /service-tickets/`
- `GET /service-tickets/<int:ticket_id>`
- `PUT /service-tickets/<int:ticket_id>`
- `DELETE /service-tickets/<int:ticket_id>`
- `PUT /service-tickets/<int:ticket_id>/edit` - **mechanic token**; bulk add/remove mechanics via `add_ids` / `remove_ids`
- `POST /service-tickets/<int:ticket_id>/add-part` - **mechanic token**; attach an inventory part with a quantity
- `PUT /service-tickets/<int:ticket_id>/assign-mechanic/<int:mechanic_id>`
- `PUT /service-tickets/<int:ticket_id>/remove-mechanic/<int:mechanic_id>`

### Inventory

- `POST /inventory/` - **mechanic token**
- `GET /inventory/`
- `GET /inventory/<int:inventory_id>`
- `PUT /inventory/<int:inventory_id>` - **mechanic token**
- `DELETE /inventory/<int:inventory_id>` - **mechanic token**

## Request examples

Create a customer (include a password to enable login):

```json
{
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane@example.com",
  "password": "secret123",
  "phone": "555-123-4567",
  "city": "Denver",
  "state": "CO",
  "postal_code": "80202"
}
```

Bulk edit a ticket's mechanics:

```json
{
  "add_ids": [1, 2],
  "remove_ids": [3]
}
```

Add a part to a ticket:

```json
{
  "inventory_id": 1,
  "quantity": 2
}
```

## Project structure

```text
mechanic-shop-api/
|-- app.py                        # dev entry point (DevelopmentConfig)
|-- config.py                     # config classes; reads DATABASE_URL, SECRET_KEY
|-- .env.example                  # placeholder values for local setup
|-- requirements.txt
|-- Mechanic Shop API.postman_collection.json
`-- app/
    |-- __init__.py               # app factory; validates config, registers blueprints
    |-- auth.py                   # JWT encode/verify, role decorators
    |-- extensions.py             # db, ma, limiter, cache
    |-- models.py                 # SQLAlchemy models + association objects
    `-- blueprints/
        |-- customers/            # /login, /my-tickets, paginated CRUD
        |-- mechanics/            # /login, /top, CRUD
        |-- service_tickets/      # CRUD, /<id>/edit, /<id>/add-part, assign/remove
        |-- inventory/            # CRUD (writes require a mechanic token)
        `-- vehicles/             # CRUD
```

## What I'd improve next

- Add a pytest suite (auth decorators, role checks, ticket ownership rule) and
  run it in CI.
- Protect the remaining write routes: mechanic, vehicle and most service
  ticket create/update/delete routes currently need no token, and mechanic
  login has no route-specific rate limit.
- Replace `db.create_all()` with Flask-Migrate migrations, and back the rate
  limiter and cache with Redis; both use in-process memory today, and the
  customer list cache is not cleared on writes, so it can be up to 60 seconds
  stale.
- Swap the deprecated `datetime.utcnow` defaults in `app/models.py` for
  timezone-aware timestamps.

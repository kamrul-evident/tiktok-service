# MYE TikTok Service

Lightweight FastAPI service and Celery worker that integrates MYE platform with TikTok Shop.

This repository provides HTTP endpoints (FastAPI) to interact with TikTok Shop APIs, background tasks (Celery) to process webhooks/products/orders, and RabbitMQ publishers/consumers to push data into MYE's queue-based pipelines.

---

**Table of contents**
- **Project**: Short project summary
- **Architecture**: Components and how they interact
- **Quick start**: Run locally (venv/pip) and with Docker
- **Configuration**: Required environment variables
- **API**: Main routes & behavior
- **Background tasks**: Celery tasks and consumers
- **Database & migrations**
- **Files of interest**

---

**Project**

- Purpose: Bridge MYE services and TikTok Shop — fetch products, update inventory, handle webhooks and orders, and publish messages to internal queues.
- Built with: `FastAPI` (HTTP API), `Celery` (async/background tasks), `SQLAlchemy` (DB models), `Kombu` / RabbitMQ (publishers/queues), `uvicorn` (ASGI server).

**Architecture (high level)**

- HTTP API (FastAPI) exposes endpoints under `/auth`, `/products`, `/orders`, `/shipping`, `/webhook`.
- `controllers/` contain request handling logic that calls `utils/maps.py` (TikTok API helpers) and triggers Celery tasks in `tasks/`.
- `tasks/` contains Celery tasks that process incoming webhook data, fetch/update products and orders, and push messages to downstream services via `publishers/`.
- `models/` stores SQLAlchemy models used to persist channels and inventory requests.
- `publishers/` send messages to RabbitMQ exchanges/queues (product/order queues) used by other MYE services.
- `consumers/` (and kombu-based worker steps) implement queue consumers for bulk inventory updates and other message-driven work.

**Quick start — Local (development)**

1. Create and activate a virtual environment (macOS / zsh):

	 ```bash
	 python3 -m venv .venv
	 source .venv/bin/activate
	 pip install -r requirements.txt
	 ```

2. Set required environment variables (see Configuration below). For development you can export them in your shell or use a `.env` loader.

3. Run the API from project root (server expects to run from the `src` folder):

	 ```bash
	 cd src
	 uvicorn main:app --reload --host 0.0.0.0 --port 8000
	 ```

4. Run Celery worker (requires RabbitMQ running and `RABBIT_URL` env configured):

	 ```bash
	 # from project root
	 celery -A config.worker.cel_app worker --loglevel=info
	 ```

**Quick start — Docker**

- This project provides a `Dockerfile` and `docker-compose.yml` for containerized runs. The `Dockerfile` builds a minimal Python image and runs `uvicorn main:app` from within `/src`.

To build and run with Docker Compose:

```bash
docker compose up --build
# or
docker-compose up --build
```

This will start the API. Ensure your `docker-compose.yml` configures RabbitMQ and Postgres services and passes env vars.

**Configuration (environment variables)**

Configuration values are loaded from environment variables in `src/config/app_vars.py` and `src/config/worker.py`.

- Database (Postgres): `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`, `DB_PORT`
- RabbitMQ: `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_HOST`, `RABBITMQ_PORT` (these are used to form `RABBIT_URL`)
- TikTok API app creds: `APP_KEY`, `APP_SECRET`
- Integration/Service URLs and secrets: `MIAMS_URL`, `MYE_ORDER_SERVICE_URL`, `INTEGRATION_SERVICE`, `MIAMS_SECRET_KEY`, `MOS_SECRET_KEY`
- Celery scheduling: `CELERY_BEAT_SCHEDULE_TIME` (seconds)
- Rabbit exchange/queue names (optional overrides): `ORDER_EXCHANGE_NAME`, `ORDER_QUEUE_NAME`, `PRODUCT_EXCHANGE_NAME`, `PRODUCT_QUEUE_NAME`, `INVENTORY_EXCHANGE_NAME`, `INVENTORY_QUEUE_NAME`

Note: A working RabbitMQ instance and a Postgres DB are required for Celery tasks and persistence.

**API — Main endpoints**

All routes are registered in `src/main.py` via routers under `src/routers/`.

- `GET /` — Health check (returns server and DB health)

- Auth endpoints (`/auth`):
	- `GET /auth/get-authorized-shops` — retrieve authorized shops using stored channel token
	- `GET /auth/get-active-shops` — retrieve active shops
	- `POST /auth/integrate-channel/` — integrate a channel (expects authorization code payload)

- Products (`/products`):
	- `GET /products/fetch-all?channel_uid=<uid>` — triggers background job to fetch all products for a channel
	- `GET /products/all?channel_uid=<uid>` — fetch paginated products from TikTok synchronously
	- `GET /products/inventory-update/multiple` — trigger background inventory update across channels
	- `GET /products/{product_id}` — get product details (requires `channel_uid` query param)
	- `POST /products/{product_id}/inventory/update` — update product inventory on TikTok (requires `channel_uid`)

- Orders (`/orders`):
	- `GET /orders` — get orders (requests TikTok for orders)
	- `GET /orders/{order_id}/` — get single order details (requires `channel_uid`)
	- `GET /orders/fetch?channel_uid=<uid>&days_ago=1` — fetch historic orders for a channel

- Shipping (`/shipping`): (calls TikTok transport APIs)
	- `GET /shipping/providers?delivery_option_id=<id>&channel_uid=<uid>` — list shipping providers
	- `GET /shipping/package/{package_id}?channel_uid=<uid>` — get package details
	- `POST /shipping/mark-shipped` — mark package shipped (expects shipping payload)
	- `POST /shipping/update` — update package shipping info

- Webhook (`/webhook`):
	- `POST /webhook/` — receives TikTok webhook payloads and queues background processing

Refer to the code in `src/routers/*.py` and `src/controllers/*.py` for precise request signatures and payload examples.

**Background tasks & queues**

- Celery app: `src/config/worker.py` (defines `cel_app`).
- Key Celery tasks in `src/tasks/` include:
	- `tasks.product.*` — fetch, create, update product tasks and background product sync
	- `tasks.order.*` — process incoming order webhooks and prepare payloads
	- `tasks.webhook.process_webhook_data` — maps webhook types to tasks (orders, messages, product events)
	- `tasks.inventory_tasks` — consumer-style worker for bulk inventory messages; inserts `InventoryRequest` records

- Publishers: `src/publishers/*` send JSON messages to RabbitMQ (order/product queues) for downstream MYE services.

**Database & Migrations**

- SQLAlchemy models live in `src/models/` (e.g., `Channel`, `InventoryRequest`).
- DB connection and Session are in `src/config/database.py` and configured via the DB env vars.
- Alembic migrations available under `src/alembic/` — use `alembic` from project root (ensure `alembic.ini` is configured) to run migrations.

**Files of interest**

- `src/main.py` — FastAPI application entrypoint and router registration
- `src/routers/*.py` — route definitions
- `src/controllers/*.py` — request handlers that orchestrate TikTok API calls and background tasks
- `src/tasks/*.py` — Celery tasks and queue worker logic
- `src/config/app_vars.py` — environment-driven configuration
- `src/config/database.py` — SQLAlchemy setup
- `src/config/worker.py` — Celery app and queues
- `src/publishers/*` — RabbitMQ publishers
- `src/consumers/*` — kombu consumer steps for inventory and product queues
- `src/utils/*` — TikTok client helpers, signature calculation, shipping helpers, and other utilities
- `Dockerfile`, `docker-compose.yml` — containerization

**How data flows (example)**

1. A TikTok webhook (order/product) arrives at `/webhook/`.
2. The webhook controller enqueues `tasks.webhook.process_webhook_data` which selects the correct task and calls `.delay()`.
3. Celery workers pick up the task and call TikTok APIs (via `utils/maps.py`) to fetch full details.
4. Tasks transform payloads and either send to internal queues via `publishers/` or call other MYE endpoints.

**Next steps / recommendations**

- Add Postman/OpenAPI examples for each endpoint and request/response payload shapes.
- Add example `.env.example` with required env variable keys and sample values.
- Add automated tests for controllers and tasks that mock external HTTP calls.

---

If you'd like, I can:
- generate a `.env.example` from the detected environment variables,
- add an `OpenAPI` examples file or Postman collection,
- or run a quick smoke test locally (if you want me to run the server and worker in this environment).

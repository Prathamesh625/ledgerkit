<div align="center">

# 🏦 LedgerKit - Transaction Ledger Service

**A double-entry transaction ledger API where money moves safely, even with retries and simultaneous requests.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

[Features](#-features) · [Architecture](#-architecture) · [Quick start](#-quick-start) · [API](#-api-overview) · [Design decisions](#-design-decisions) · [Testing](#-testing) · [Runbook](docs/RUNBOOK.md)

</div>

> ⚠️ **Learning project.** This is a sandbox built to demonstrate backend engineering practices. It is not a real banking system and uses only synthetic data.

---

## 📌 Why this project exists

Moving money looks simple until real-world problems appear:

| Problem | What goes wrong | How this project handles it |
|---|---|---|
| **Client retries** | A timeout makes the client resend, and the payment posts twice | **Idempotency keys** return the original result |
| **Simultaneous requests** | Two withdrawals read the same balance and overdraw the account | **Row-level locking** inside DB transactions |
| **Partial failures** | A debit succeeds but the credit fails | **Atomic transactions**, so both entries post or neither does |
| **"Where did the money go?"** | No way to trace a discrepancy | **Double-entry ledger, audit log, reconciliation endpoint** |

## ✨ Features

- **Double-entry bookkeeping:** every transfer creates a balanced debit and credit entry
- **Idempotent payments:** safe to retry using an `Idempotency-Key` header
- **Concurrency-safe balances:** `SELECT ... FOR UPDATE` row locking, verified by a parallel-request test
- **JWT authentication** with hashed passwords
- **Audit log** recording who did what and when
- **Reconciliation endpoint** that detects balance mismatches against ledger entries
- **Structured JSON logging** with a request ID for tracing
- **Operational dashboard** (HTML/CSS/JS) for balances and recent transactions
- **Alembic migrations**, **Docker Compose** setup, and **GitHub Actions CI**
- **[Runbook](docs/RUNBOOK.md)** for payment failures, duplicate requests and balance mismatches

## 🧱 Architecture

```mermaid
flowchart LR
    C[Client / Dashboard] -->|HTTPS + JWT| A[FastAPI app]
    A --> S[Ledger service<br/>idempotency + locking]
    S --> D[(PostgreSQL)]
    A --> L[Structured JSON logs]
    S --> AU[(Audit log table)]
```

**Idempotent transfer flow**

```mermaid
sequenceDiagram
    participant C as Client
    participant API as FastAPI
    participant DB as PostgreSQL
    C->>API: POST /transfers (Idempotency-Key: k1)
    API->>DB: BEGIN, check key k1
    alt key already used
        DB-->>API: stored response
        API-->>C: 200 original result (no new posting)
    else new key
        API->>DB: lock both accounts (ordered)
        API->>DB: insert debit + credit entries
        API->>DB: store key + response, COMMIT
        API-->>C: 201 Created
    end
```

## 🧰 Tech stack

| Layer | Tools |
|---|---|
| API | Python, FastAPI, Pydantic |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Auth | JWT, password hashing (bcrypt) |
| Testing | pytest, pytest-asyncio, coverage |
| DevOps | Docker, Docker Compose, GitHub Actions |
| Frontend | HTML, CSS, JavaScript |

## 🚀 Quick start

**Prerequisites:** Docker and Docker Compose

```bash
# 1. Clone
git clone https://github.com/Prathamesh625/safe-ledger-api.git
cd safe-ledger-api

# 2. Configure
cp .env.example .env

# 3. Start the API and database
docker compose up --build

# 4. Run migrations
docker compose exec api alembic upgrade head
```

- API docs (Swagger): http://localhost:8000/docs
- Dashboard: http://localhost:8000/dashboard
- Health check: http://localhost:8000/health

**Generate mock data**

```bash
docker compose exec api python scripts/generate_mock_transactions.py --count 10000
```

## 📡 API overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a user |
| `POST` | `/auth/login` | Get a JWT |
| `POST` | `/accounts` | Open an account |
| `GET` | `/accounts/{id}` | Balance and details |
| `POST` | `/accounts/{id}/deposit` | Deposit funds |
| `POST` | `/accounts/{id}/withdraw` | Withdraw funds (rejects overdraft) |
| `POST` | `/transfers` | Transfer between accounts (**requires `Idempotency-Key`**) |
| `GET` | `/accounts/{id}/transactions` | Paginated history |
| `GET` | `/reconciliation` | Compare balances with ledger entries |
| `GET` | `/health` | Liveness check |

**Example: idempotent transfer**

```bash
curl -X POST http://localhost:8000/transfers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: 7c9e6679-7425-40de-944b-e07fc1f90ae7" \
  -H "Content-Type: application/json" \
  -d '{"from_account": 1, "to_account": 2, "amount": "250.00"}'
```

Sending the same request again returns the **same response** and posts **nothing new**.

## 🧠 Design decisions

**Why double-entry?**
Every transfer writes a debit and a credit that sum to zero. If the totals ever disagree, there is a bug, and the reconciliation endpoint can find it.

**Why PostgreSQL row locking instead of application locks?**
Locks in application memory break the moment you run two API instances. `SELECT ... FOR UPDATE` puts the guarantee in the database, which is the single source of truth.

**How are deadlocks avoided?**
Transfers lock accounts in a fixed order (lowest ID first), so two opposite transfers (A to B and B to A) cannot wait on each other.

**Why store money as `NUMERIC`, not float?**
Floats cause rounding errors (`0.1 + 0.2 != 0.3`). Amounts use `Decimal` in Python and `NUMERIC(18,2)` in PostgreSQL.

**How does idempotency work?**
The key and the stored response are written in the same transaction as the postings. If the transaction commits, the key exists. If it rolls back, it doesn't, so a retry is safe. A unique constraint on the key stops two simultaneous requests with the same key from both posting.

**What I would improve next:** background reconciliation job, rate limiting, per-user roles, and a message queue for async notifications.

## 🧪 Testing

```bash
docker compose exec api pytest --cov=app
```

| Test type | What it proves |
|---|---|
| Unit | Ledger math, validation, amount handling |
| Integration | Endpoints, auth, error responses |
| **Idempotency** | The same key sent 5 times creates exactly 1 posting |
| **Concurrency** | 50 parallel withdrawals never push the balance below zero |
| Reconciliation | A deliberately corrupted balance is detected |

### The concurrency test (the interesting one)

1. Without locking, the 50 parallel withdrawals **overdrew the account** (balance went negative).
2. After adding `SELECT ... FOR UPDATE`, the same test passes consistently.

> 📝 *TODO: record the actual numbers you observed (e.g. final balance before the fix, number of successful vs rejected withdrawals after the fix).*

## 📊 Results

> Fill these in only with numbers you measured, and keep the command used next to each one.

| Metric | Result | How measured |
|---|---|---|
| Test count | _TODO_ | `pytest` |
| Coverage | _TODO_ | `pytest --cov` |
| Mock transactions generated | _TODO_ | `scripts/generate_mock_transactions.py` |
| p95 latency, `/transfers` | _TODO_ | Locust, _N_ users |

## 🗂️ Project structure

```
ledgerkit/
├── app/
│   ├── main.py
│   ├── api/          # routes: accounts, transfers, reconciliation
│   ├── core/         # config, JWT security, logging
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # ledger logic, idempotency
│   └── static/       # dashboard HTML/CSS/JS
├── alembic/          # migrations
├── tests/            # unit, integration, concurrency
├── scripts/          # mock data generator
├── docs/             # RUNBOOK.md, architecture notes
├── docker-compose.yml
└── Dockerfile
```

## 🛠️ Operations and support

See the **[Runbook](docs/RUNBOOK.md)** for step-by-step guides:

- A payment failed: how to investigate
- A duplicate request arrived: how idempotency resolves it
- Balance mismatch: how to reconcile

## 🐞 Problems I faced

- TODO: parallel withdrawals overdrew an account until I added row locking.
- TODO: opposite transfers deadlocked until I locked accounts in ID order.

> Replace these with your real notes. A few honest entries here are worth more than any badge.

## 🗺️ Roadmap

- [ ] Background reconciliation job
- [ ] Rate limiting
- [ ] Role-based access control
- [ ] Prometheus metrics

## 📄 License

MIT. See [LICENSE](LICENSE).

---

<div align="center">

Built by [Prathamesh Thorat](https://github.com/Prathamesh625) · [LinkedIn](https://linkedin.com/in/thoratprathamesh625)

</div>
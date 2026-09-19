# Baltazar CRM

# Technical Specification & Architecture Document

| Attribute | Value |
|-----------|--------|
| **Document type** | Production-grade Technical Specification & Architecture |
| **Project** | Baltazar CRM (CRM-Baltazar) |
| **Version** | 1.0.0 |
| **Status** | Living document — aligned with the current codebase |
| **Primary language** | Application UI: Persian (RTL); this specification: English |
| **License** | MIT |
| **Repository** | https://github.com/WhileTrue0087/CRM-Baltazar |
| **Reference deployment** | https://crm-baltazar.onrender.com/ |

---

## Table of contents

1. [System Overview](#1-system-overview)
2. [Architecture & Design](#2-architecture--design)
3. [Database & Data Modeling](#3-database--data-modeling)
4. [API / Interface Reference](#4-api--interface-reference)
5. [Configuration & Environment](#5-configuration--environment)
6. [Deployment & DevOps](#6-deployment--devops)
7. [Security & Error Handling](#7-security--error-handling)

---

## 1. System Overview

### 1.1 Executive summary

**Baltazar CRM** is a self-hosted, sequential sales-pipeline CRM that enforces a five-stage funnel:

**Lead Hunter (LH) → SDR → Setter → PM → Closer**, with a sixth **Admin** persona for operations, analytics, user management, Excel import/export, and equal lead distribution.

The product replaces unstructured spreadsheets and ad-hoc follow-ups with:

- Role-specific dashboards and queues
- Enforced stage transitions (no skipping the intended workflow)
- Duplicate-phone detection on intake
- Jalali (Persian) calendar for operations in Iran (`Asia/Tehran`)
- Soft-delete / archive with an audit trail (who archived, why)
- Gamified scoring when Setter **approves** a meeting (`+1` to responsible LH and SDR)

The application is a **modular Flask monolith**: server-rendered Jinja2 templates (Tailwind via CDN), WTForms + CSRF, Flask-Login sessions, and SQLAlchemy 2.x against SQLite by default (any SQLAlchemy URI, including PostgreSQL, via `DATABASE_URL`).

### 1.2 Domain, stakeholders, and business problem

| Stakeholder | Role in domain | System goal |
|-------------|----------------|-------------|
| Sales operations / management | Admin | Funnel visibility, daily metrics, Excel reports, user lifecycle, bulk import, fair SDR assignment |
| Lead Hunters | LH | Structured intake (company, up to 3 phones, source, business type); fix wrong numbers returned by SDR |
| SDR team | SDR | Call outcomes, qualification, routing to Setter or PM, follow-up dates, archive/disqualify |
| Appointment setters | Setter | Approve / reject / uncertain meetings; approved meetings advance to Closer and award scores |
| Proposal managers | PM | Jalali-dated proposals with amount validation; mark proposal sent for SDR follow-up |
| Closers | Closer | Meeting held/not held; won / lost / follow-up |
| Engineering / DevOps | Operators | Deploy, backup SQLite/Postgres, rotate secrets, scale Gunicorn workers |

**Technical problem statement:** Multi-stage B2B outreach in Persian-speaking markets needs a single source of truth, RTL UX, Persian digits/dates, phone normalization (Persian/Arabic digits), and role isolation so each team only acts on leads they own or that sit in their queue.

### 1.3 Scope

**In scope**

- Authentication (username/password), role-based access control (RBAC)
- Full pipeline state machine on the `leads` table (wide-row / document-in-table pattern)
- Admin CRUD for users and leads; soft then hard delete
- Search by company name, business type, source
- Leaderboard (rating board) modal
- Excel bulk import (columns B/C/D from row 2) and department exports
- Equal distribution of unassigned stage-2 leads (today vs backlog) among selected active SDRs
- Lightweight SQLite schema patches on startup (`apply_schema_patches`)

**Out of scope (current product)**

- Public REST/GraphQL API for third-party CRM sync
- Email/SMS/telephony integrations
- Multi-tenant SaaS isolation
- Native mobile apps
- Kubernetes manifests in-repo (recommended patterns are specified in Chapter 6)
- Automated test suite / GitHub Actions (recommended pipeline is specified in Chapter 6)

### 1.4 Technical objectives

| ID | Objective | Success criterion |
|----|-----------|-------------------|
| T1 | Single-process, factory-based Flask app | `create_app()` in `app/__init__.py`; WSGI entry `run:app` |
| T2 | Role isolation | `@role_required(...)` + 403 template; SDR ownership checks |
| T3 | Pipeline integrity | Stage/status transitions only via documented workflow functions and role forms |
| T4 | Data durability | SQLAlchemy models; `db.create_all()` + ALTER patches for SQLite |
| T5 | Localization | Jalali via `jdatetime`; Tehran TZ via `zoneinfo` |
| T6 | Operational visibility | Admin daily metrics hybrid (today + totals); print reports |
| T7 | Production readiness | Gunicorn/Waitress; env-based `SECRET_KEY` and `DATABASE_URL`; 16 MB upload cap |

### 1.5 High-level constraints

- **Monolith, not microservices.** Domain modules are Flask blueprints + service functions, not independently deployable services.
- **Server-side rendering first.** Most “APIs” are HTML form POST endpoints. One JSON JSON endpoint exists for admin user analytics.
- **SQLite-friendly migrations.** There is no Alembic. Column additions are listed in `SCHEMA_PATCHES`. Destructive resets use `python seed.py --reset`.
- **Demo credentials** (`admin` / `admin123`, etc.) are for local seed only and must never ship to production unchanged.

---

## 2. Architecture & Design

### 2.1 Architectural style

| Dimension | Choice | Rationale |
|-----------|--------|-----------|
| Style | Modular monolith | Small team, shared `Lead` aggregate, transactional stage updates |
| Presentation | Jinja2 + Tailwind CDN + Dana font | Fast RTL dashboards without a separate SPA |
| Persistence | SQLAlchemy ORM, two tables (`users`, `leads`) | Pipeline fields denormalized onto `Lead` for simple queries |
| AuthN | Flask-Login cookie session | Fits form-based UI |
| AuthZ | Role string on `User` + decorator | Six discrete roles |
| Background jobs | None | Distribution and scoring run in request thread |
| File I/O | pandas/openpyxl in-memory buffers | Import upload; export `send_file` |

**Logical layers**

1. **HTTP / Blueprint layer** — routes, flash messages, `abort(404)`, redirects  
2. **Form / validation layer** — Flask-WTF, custom Jalali fields, phone validators  
3. **Service layer** — `lead_workflow`, `sdr_assignment`, `sdr_queue`, `scoring`, `daily_metrics`, `excel_*`, `leaderboard`, `user_analytics`  
4. **Domain / ORM layer** — `User`, `Lead` (+ properties that encode queue membership)  
5. **Infrastructure** — `extensions.py` (`db`, `bcrypt`, `csrf`, `login_manager`), `config.py`, `db_migrate.py`

### 2.2 High-level architecture (flowchart)

```mermaid
flowchart TB
  subgraph Clients
    B[Browser RTL UI]
  end

  subgraph Edge
    W[WSGI: Gunicorn / Waitress / Flask dev]
  end

  subgraph App["Flask application factory create_app()"]
    AUTH[auth blueprint]
    LH[lh blueprint]
    SDR[sdr blueprint]
    SET[setter blueprint]
    PM[pm blueprint]
    CL[closer blueprint]
    ADM[admin blueprint]
    SRCH[search blueprint]
    SH[shared rating-board]
  end

  subgraph Services
    WF[lead_workflow]
    ASGN[sdr_assignment]
    Q[sdr_queue]
    SC[scoring]
    XL[excel import/export]
    MET[daily_metrics]
  end

  subgraph Data
    ORM[SQLAlchemy]
    DB[(SQLite / PostgreSQL)]
  end

  B --> W --> AUTH
  W --> LH & SDR & SET & PM & CL & ADM & SRCH & SH
  LH --> WF
  SDR --> WF
  SET --> SC
  ADM --> ASGN
  ADM --> XL
  ADM --> MET
  SDR --> Q
  LH & SDR & SET & PM & CL & ADM --> ORM --> DB
```

### 2.3 Pipeline sequence (happy path)

```mermaid
sequenceDiagram
  participant LH as Lead Hunter
  participant App as Flask
  participant DB as Database
  participant Admin as Admin
  participant SDR as SDR
  participant Setter as Setter
  participant PM as PM
  participant Closer as Closer

  LH->>App: POST /lh/ intake form
  App->>App: normalize phones, duplicate check
  App->>DB: INSERT lead stage=2, unassigned
  Admin->>App: POST /admin/lead-distribution
  App->>DB: assign assigned_sdr_id round-robin
  SDR->>App: POST /sdr/lead/{id}/process
  alt Route to Setter
    App->>DB: stage=3, sdr_next_action=انتقال به setter
    Setter->>App: POST approve meeting
    App->>DB: stage=5, +1 score LH and SDR
    Closer->>App: POST won/lost/follow-up
  else Route to PM
    App->>DB: stage=4, sdr_routed_to_pm=true
    PM->>App: POST submit-proposal
    App->>DB: proposal_status=sent, pm_proposal_ready=true
    SDR->>App: proposal follow-up queue
  else Wrong number
    App->>DB: stage=1, call_status=شماره اشتباه
    LH->>App: POST fix-wrong-number
    App->>DB: clear SDR fields, back to SDR pool
  end
```

### 2.4 Request data flow (typical mutating POST)

1. Browser submits form including CSRF token (`Flask-WTF`).
2. Blueprint handler applies `@role_required`.
3. Additional ownership rules (e.g. SDR `assigned_sdr_id == current_user.id`; LH `created_by_id`).
4. Form `validate_on_submit()` or manual field checks (PM proposal).
5. Service or inline mapper updates `Lead` columns and `updated_at`.
6. `db.session.commit()`.
7. Flash + redirect (Post/Redirect/Get).

### 2.5 Key modules / entities

| Module | Path | Responsibility |
|--------|------|----------------|
| Application factory | `app/__init__.py` | Config, extensions, blueprints, user loader, `db.create_all`, schema patches, 403 handler, Jinja context (labels, Jalali formatters) |
| Config | `app/config.py` | Secrets, DB URI, CSRF, upload size, stage/role/pipeline labels, dashboard endpoint map |
| Extensions | `app/extensions.py` | SQLAlchemy, Bcrypt, CSRFProtect, LoginManager |
| Models | `app/models.py` | `User`, `Lead`, UTC `utcnow()`, queue/archive computed properties |
| Auth | `app/blueprints/auth` | Login/logout |
| LH | `app/blueprints/lh` | Intake, wrong-number repair |
| SDR | `app/blueprints/sdr` | Call processing, daily Excel |
| Setter | `app/blueprints/setter` | Meeting outcomes, scoring trigger |
| PM | `app/blueprints/pm` | Proposal submit |
| Closer | `app/blueprints/closer` | Deal close |
| Admin | `app/blueprints/admin` | Metrics, users, leads, import/export, distribution |
| Search | `app/blueprints/search` | Authenticated lead search |
| Shared | `app/blueprints/shared` | Rating board HTML fragment |
| Decorators | `app/utils/decorators.py` | `role_required`, `redirect_to_role_dashboard` |
| Phone | `app/utils/phone.py` | Digit maps, `09…` prefix, duplicate scan |
| Dates | `app/utils/jalali_dates.py` | Tehran TZ, Jalali format/parse, UTC day range |
| Forms | `app/forms/*` | Role forms, admin user/lead/import, Jalali widgets |
| Seed | `seed.py` | Demo users + sample leads |
| WSGI | `run.py` | Dev server + Gunicorn target |
| Windows/IP bind | `run_server.py` | Waitress on a fixed host IP (environment-specific) |

**Classes (ORM)**

- `User(UserMixin)` — identity, bcrypt hash, optional `password_plain` (see Security), `role`, `is_active`, `score`
- `Lead` — single aggregate for the entire funnel (see schema)

**Constants on `Lead`** encode Persian workflow strings used as stored values (call status, next actions, setter/closer statuses). Do not rename without a data migration.

### 2.6 Directory / folder structure

```
CRM/
├── app/
│   ├── __init__.py                 # create_app, blueprint registration
│   ├── config.py
│   ├── extensions.py
│   ├── models.py
│   ├── choices.py               # shared filter choices (business type, source)
│   ├── blueprints/
│   │   ├── auth/                # url_prefix=/auth
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   ├── lh/                  # /lh
│   │   ├── sdr/                 # /sdr
│   │   ├── setter/              # /setter
│   │   ├── pm/                  # /pm
│   │   ├── closer/               # /closer
│   │   ├── admin/               # /admin
│   │   ├── search/               # /search
│   │   └── shared/               # /rating-board/modal
│   ├── forms/
│   │   ├── auth_forms.py
│   │   ├── lh_forms.py
│   │   ├── sdr_forms.py
│   │   ├── setter_forms.py
│   │   ├── pm_forms.py
│   │   ├── closer_forms.py
│   │   ├── admin_forms.py
│   │   ├── search_forms.py
│   │   └── jalali_fields.py
│   ├── services/
│   │   ├── lead_workflow.py
│   │   ├── sdr_assignment.py
│   │   ├── sdr_queue.py
│   │   ├── scoring.py
│   │   ├── daily_metrics.py
│   │   ├── user_analytics.py
│   │   ├── leaderboard.py
│   │   ├── excel_import.py
│   │   └── excel_export.py
│   ├── utils/
│   │   ├── decorators.py
│   │   ├── phone.py
│   │   ├── jalali_dates.py
│   │   └── db_migrate.py
│   ├── templates/               # Jinja2 (RTL)
│   │   ├── base.html
│   │   ├── errors/403.html
│   │   ├── auth/, lh/, sdr/, setter/, pm/, closer/, admin/, search/
│   │   └── partials/
│   └── static/
│       └── fonts/             # Dana-Black.ttf (referenced from base.html)
├── instance/                    # created at runtime; crm.db (gitignored)
├── seed.py
├── run.py
├── run_server.py
├── requirements.txt
├── Procfile                     # Render/Heroku: gunicorn run:app
├── .gitignore
├── README.md
├── LICENSE
└── full-document.md            # this specification
```

### 2.7 Frontend architecture notes

- **No SPA router.** Each role dashboard is a full page load.
- **Styling:** Tailwind Play CDN (`https://cdn.tailwindcss.com`) — acceptable for internal CRM; production hardening should pin a built CSS bundle (see DevOps).
- **CSRF:** Hidden field via `partials/csrf_input.html` on POSTs.
- **Modals:** Rating board loaded from `/rating-board/modal`; admin lead detail via HTML partials.

---

## 3. Database & Data Modeling

### 3.1 Entity-relationship overview

There are **two physical tables**. The `Lead` row is a **wide aggregate**: LH identity, SDR assignment and call sheet, Setter meeting, PM proposal, Closer outcome, and admin archive metadata all live on one record. Relationships to `users` are multiple optional FKs (created_by, assigned SDR, processing agents, admin deleter).

```mermaid
erDiagram
  users ||--o{ leads : created_by
  users ||--o{ leads : assigned_sdr
  users ||--o{ leads : sdr_agent
  users ||--o{ leads : setter_agent
  users ||--o{ leads : pm_agent
  users ||--o{ leads : closer_agent
  users ||--o{ leads : admin_deleted_by

  users {
    int id PK
    string username UK
    string password_hash
    string password_plain
    string role
    bool is_active
    int score
    datetime created_at
  }

  leads {
    int id PK
    int current_stage
    string pipeline_status
    datetime created_at
    datetime updated_at
    datetime admin_deleted_at
    int admin_deleted_by_id FK
    int created_by_id FK
    string company_name
    string phone_number
    string phone_number_2
    string phone_number_3
    int phone_primary
    int assigned_sdr_id FK
    int sdr_agent_id FK
    int setter_agent_id FK
    int pm_agent_id FK
    int closer_agent_id FK
  }
```

**Cardinality rules**

- One user has many leads they created (`created_by_id`).
- A lead has at most one assigned SDR, one SDR agent (who last processed the call), one setter/PM/closer agent.
- Deleting a user nulls `created_by_id` on their leads (admin delete-user path) then removes the user row.

### 3.2 Pipeline state machine (data flow)

| `current_stage` | Label (config) | Typical `pipeline_status` | Entry condition |
|-----------------|----------------|---------------------------|-----------------|
| 1 | شکارچی سرنخ (LH) | `active` | Wrong-number return from SDR |
| 2 | SDR | `active` / `disqualified` | LH intake or re-queue; SDR follow-up/delete |
| 3 | ستر | `active` / `disqualified` | SDR next action «انتقال به setter» |
| 4 | مدیر پیشنهاد (PM) | `active` | SDR next action «ارسال اطلاعات (پروپوزال)» |
| 5 | کلوزر | `active` / `closed_won` / `closed_lost` | Setter approved meeting |

**SDR next-action stored values**

| Stored value | Effect |
|--------------|--------|
| `انتقال به setter` | `current_stage = 3` |
| `ارسال اطلاعات (پروپوزال)` | `current_stage = 4`, `sdr_routed_to_pm = True` |
| `تماس بعدی در تاریخ مشخص` | stay stage 2, follow-up queue |
| `حذف` | `pipeline_status = disqualified` (or archived list) |

**Setter statuses:** `تایید شده` → stage 5 + scores; `رد شده` → disqualified; `نامشخص نیاز به پیگیری مجدد` → setter follow-up queue.

**Closer cooperation:** `موفق` → `closed_won`; `رد` → `closed_lost`; `پیگیری مجدد` → remain `active` stage 5.

**Soft delete:** `admin_deleted_at` set; operational queries use `Lead.active_only()` (`admin_deleted_at IS NULL`). Second admin delete **hard-deletes** the row.

### 3.3 Schema breakdown — `users`

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | INTEGER | Surrogate key | PK, autoincrement |
| `username` | VARCHAR(80) | Login identifier | NOT NULL, UNIQUE, indexed |
| `password_hash` | VARCHAR(128) | Bcrypt hash | NOT NULL |
| `password_plain` | VARCHAR(128) | **Plaintext copy for admin UI copy/blur** | NULL allowed; **must not be used in production** |
| `role` | VARCHAR(20) | `admin`, `lh`, `sdr`, `setter`, `pm`, `closer` | NOT NULL, indexed |
| `is_active` | BOOLEAN | Suspended users cannot log in | NOT NULL, default True |
| `score` | INTEGER | Leaderboard points | NOT NULL, default 0 |
| `created_at` | DATETIME | UTC creation | NOT NULL, default `utcnow()` |

### 3.4 Schema breakdown — `leads` (identity, LH, archive)

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | INTEGER | Lead ID | PK |
| `current_stage` | INTEGER | 1–5 | NOT NULL, default 1, indexed |
| `pipeline_status` | VARCHAR(20) | `active`, `disqualified`, `closed_won`, `closed_lost` | NOT NULL, default `active`, indexed |
| `created_at` | DATETIME | UTC | NOT NULL |
| `updated_at` | DATETIME | UTC, onupdate | NOT NULL |
| `admin_deleted_at` | DATETIME | Soft-delete timestamp | Indexed, nullable |
| `admin_deleted_by_id` | INTEGER | FK → `users.id` | Indexed, nullable |
| `created_by_id` | INTEGER | LH (or importer) | FK, indexed, nullable |
| `company_name` | VARCHAR(200) | Business name | NOT NULL, indexed |
| `phone_number` | VARCHAR(40) | Primary/storage slot 1 | NOT NULL |
| `phone_number_2` | VARCHAR(40) | Backup | Nullable |
| `phone_number_3` | VARCHAR(40) | Backup | Nullable |
| `phone_primary` | INTEGER | Which slot is “golden” (1–3) | NOT NULL, default 1 |
| `business_type` | VARCHAR(80) | Catalog or «سایر» | NOT NULL |
| `business_type_custom` | VARCHAR(120) | When type is «سایر» | Nullable |
| `source` | VARCHAR(80) | Catalog, «سایر», or `آپلود اکسل` | NOT NULL |
| `source_custom` | VARCHAR(120) | When source is «سایر» | Nullable |
| `website` | VARCHAR(255) | URL | Nullable |
| `telegram` | VARCHAR(120) | Handle | Nullable |
| `instagram` | VARCHAR(120) | Handle | Nullable |
| `address` | TEXT | Location | Nullable |
| `description` | TEXT | LH notes | Nullable |

### 3.5 Schema breakdown — `leads` (SDR)

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `assigned_sdr_id` | INTEGER | Queue owner | FK, indexed |
| `assigned_sdr_at` | DATETIME | Assignment time (rollover detection) | Nullable |
| `sdr_call_status` | VARCHAR(40) | پاسخ داد / پاسخ نداد / شماره اشتباه / تماس قطع شده | Nullable |
| `sdr_result` | VARCHAR(60) | جلسه هماهنگ شود / رد شده / دوباره باید پیگیری شود | Nullable |
| `sdr_rejection_reason` | TEXT | Reject reason | Nullable |
| `sdr_pain_severity` | VARCHAR(20) | کم / متوسط / زیاد | Nullable |
| `sdr_buying_power` | VARCHAR(20) | پایین / متوسط / بالا / نامشخص | Nullable |
| `sdr_contact_person` | VARCHAR(30) | مدیر / مالک / کارمند / نامشخص | Nullable |
| `sdr_contact_name` | VARCHAR(120) | Required for some contact types | Nullable |
| `sdr_interest_level` | VARCHAR(20) | سرد / معمولی / گرم | Nullable |
| `sdr_next_action` | VARCHAR(60) | Routing / follow-up / delete | Indexed |
| `sdr_followup_date` | DATE | Next call (Gregorian date) | Nullable |
| `wrong_number_type` | VARCHAR(60) | خود شماره… / صاحب شماره… | Nullable |
| `wrong_number_notes` | TEXT | Wrong-number detail | Nullable |
| `sdr_summary` | TEXT | Call notes | Nullable |
| `sdr_agent_id` | INTEGER | Processor | FK, indexed |
| `sdr_processed_at` | DATETIME | Last SDR submit | Nullable |
| `sdr_routed_to_pm` | BOOLEAN | PM path flag | NOT NULL, default False |
| `pm_proposal_ready` | BOOLEAN | PM completed proposal | NOT NULL, default False |
| `proposal_status` | VARCHAR(20) | `pending` / `sent` | NOT NULL, default `pending`, indexed |

### 3.6 Schema breakdown — `leads` (Setter, PM, Closer)

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `setter_status` | VARCHAR(50) | Approved / rejected / uncertain | Indexed |
| `setter_meeting_date` | DATETIME | Meeting datetime | Nullable |
| `setter_meeting_location` | TEXT | Place | Nullable |
| `setter_notes` | TEXT | Setter notes | Nullable |
| `setter_agent_id` | INTEGER | FK | Indexed |
| `pm_agent_id` | INTEGER | FK | Indexed |
| `proposal_title` | VARCHAR(200) | Title | Nullable |
| `proposal_amount` | FLOAT | Amount (non-negative) | Nullable |
| `proposal_details` | TEXT | Min 10 chars on submit | Nullable |
| `proposal_date` | DATE | Jalali-entered, stored Gregorian | Nullable |
| `closer_meeting_status` | VARCHAR(30) | برگزار شد / برگزار نشد | Nullable |
| `closer_cooperation_status` | VARCHAR(30) | موفق / پیگیری مجدد / رد | Indexed |
| `closer_followup_date` | DATETIME | Closer follow-up | Nullable |
| `closer_notes` | TEXT | Closer notes | Nullable |
| `closer_agent_id` | INTEGER | FK | Indexed |
| `deal_outcome` | VARCHAR(20) | `won` / `lost` | Nullable |
| `closing_notes` | TEXT | Copied from closer notes on submit | Nullable |
| `closed_at` | DATETIME | Close timestamp | Nullable |

### 3.7 Indexes and query patterns

- **SDR dashboard:** `assigned_sdr_id` + `current_stage` + `pipeline_status` + `sdr_next_action`; carryover uses `assigned_sdr_at` vs Tehran “today”.
- **Setter dashboard:** `sdr_next_action` + `current_stage` + `setter_status`.
- **PM:** `current_stage == 4` and `pipeline_status == active`.
- **Search:** `company_name ILIKE`, equality on `business_type` and `source`.
- **Duplicate phones:** Currently **application-level scan** of all active leads (not a unique DB constraint). Production scale should add a normalized-phone table or unique index on a computed digit string.

### 3.8 Schema evolution

`app/utils/db_migrate.py` applies `ALTER TABLE ... ADD COLUMN` when columns listed in `SCHEMA_PATCHES` are missing (SQLite `PRAGMA table_info`; other dialects via inspector). **It does not drop columns or rewrite enums.** After incompatible model changes, operators use `python seed.py --reset` (destructive).

---

## 4. API / Interface Reference

This system is **not a public JSON API**. The interface is **HTTP + HTML forms** (and file downloads). Below, each route is specified as an enterprise contract: method, auth, status codes, and payload shape.

**Conventions**

- **Auth:** Session cookie after `POST /auth/login`. Unauthenticated users hitting protected pages are redirected to `/auth/login` (302) with Flask-Login message.
- **RBAC failure:** `403` + `templates/errors/403.html`.
- **Missing lead:** `404` (`abort(404)`).
- **Success mutations:** `302` redirect + flashed message (not JSON).
- **CSRF:** All POST forms require a valid CSRF token. Missing/invalid token → **400** (Flask-WTF default).

### 4.1 HTTP status codes (system-wide)

| Code | When |
|------|------|
| 200 | GET pages, successful JSON analytics, file download body |
| 302 | Login, logout, successful form POST (PRG), role dashboard redirect from `/` |
| 400 | CSRF failure, malformed request |
| 403 | Authenticated but wrong role |
| 404 | Unknown lead/user where `abort(404)` is used |
| 413 | Upload exceeds `MAX_CONTENT_LENGTH` (16 MB) |
| 500 | Unhandled exception (Excel parse is caught and flashed instead) |

### 4.2 Root and authentication

#### `GET /`

| Item | Detail |
|------|--------|
| Auth | Public |
| Behavior | If authenticated → redirect to role dashboard; else → `/auth/login` |
| Status | 302 |

#### `GET|POST /auth/login`

**GET 200** — login form.

**POST** — `application/x-www-form-urlencoded`

```http
POST /auth/login HTTP/1.1
Content-Type: application/x-www-form-urlencoded

csrf_token=...&username=admin&password=admin123&submit=...
```

| Result | Status | Body |
|-------|--------|------|
| Success | 302 | Location: role dashboard (`/admin/`, `/lh/`, …) |
| Bad credentials / suspended | 200 | Re-rendered login + flash |
| Already logged in | 302 | Role dashboard |

**Logical request JSON (for integrators mapping forms):**

```json
{
  "username": "admin",
  "password": "********"
}
```

#### `GET /auth/logout`

| Auth | Session |
|-------|---------|
| Status | 302 to `/auth/login` |

### 4.3 Lead Hunter (`/lh`)

Role: **`lh`**.

| Method | Path | Description |
|-------|------|-------------|
| GET/POST | `/lh/` | Dashboard + intake |
| GET/POST | `/lh/lead/<id>/fix-wrong-number` | Repair wrong number; must be creator, stage 1, call status شماره اشتباه |
| GET | `/lh/leads/new` | 302 to `/lh/` |

**POST `/lh/` sample fields**

```json
{
  "company_name": "کلینیک زیبای رز",
  "phone_number": "09121234567",
  "phone_backup": ["02188776655"],
  "business_type": "کلینیک زیبایی",
  "source": "نشان",
  "website": "https://example.com",
  "telegram": "@clinic",
  "instagram": "@clinic",
  "address": "تهران",
  "description": "..."
}
```

**Outcomes**

- Duplicate phone → 200 re-render + danger flash (`این شماره تماس قبلاً در سیستم ثبت شده است...`).
- Success → 302 `/lh/`, lead inserted with `current_stage=2`, `assigned_sdr_id=NULL` (pool).

### 4.4 SDR (`/sdr`)

Role: **`sdr`**. Process allowed only if `assigned_sdr_id == current_user.id`.

| Method | Path | Description |
|-------|------|-------------|
| GET | `/sdr/` | Queues: new inbound (rollover-first), follow-up, deleted, PM proposal follow-up |
| GET/POST | `/sdr/lead/<id>/process` | Call form |
| GET | `/sdr/export/today-excel` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |

**POST process — answered call routed to Setter**

```json
{
  "sdr_call_status": "پاسخ داد",
  "sdr_result": "جلسه هماهنگ شود",
  "sdr_pain_severity": "متوسط",
  "sdr_buying_power": "بالا",
  "sdr_contact_person": "مالک",
  "sdr_contact_name": "علی",
  "sdr_interest_level": "گرم",
  "sdr_next_action": "انتقال به setter",
  "sdr_summary": "علاقه‌مند به جلسه"
}
```

**Wrong number** — lead returned to LH (`current_stage=1`).

**Unanswered** — optional next action delete/follow-up; may stay stage 2.

If lead not assigned to caller → 302 dashboard + warning (not 403).

### 4.5 Setter (`/setter`)

Role: **`setter`**.

| Method | Path | Description |
|-------|------|-------------|
| GET | `/setter/` | New / follow-up / rejected lists |
| GET/POST | `/setter/lead/<id>/process` | Meeting form; first-time approve awards scores |
| GET | `/setter/lead/<id>` | 302 to process |

**POST sample**

```json
{
  "setter_status": "تایید شده",
  "setter_meeting_date": "2026-09-01T10:00:00",
  "setter_meeting_location": "دفتر مرکزی",
  "setter_notes": "هماهنگ شد"
}
```

### 4.6 PM (`/pm`)

Role: **`pm`**.

| Method | Path | Description |
|-------|------|-------------|
| GET | `/pm/` | Stage-4 active leads |
| POST | `/pm/lead/<id>/submit-proposal` | Create proposal |
| POST | `/pm/lead/<id>/proposal-ready` | Legacy; 302 to dashboard hash |

**POST submit-proposal** (form fields, not WTForms class)

| Field | Validation |
|-------|----------|
| `proposal_title` | Required non-empty |
| `proposal_amount` | `float >= 0` |
| `proposal_date` | Jalali `YYYY/MM/DD` via `parse_jalali_date` |
| `proposal_details` | Length ≥ 10 |

Success sets `proposal_status=sent`, `pm_proposal_ready=True`, `pm_agent_id`.

Invalid input → 302 dashboard `#lead-{id}` + flash (still 302, not 422).

### 4.7 Closer (`/closer`)

Role: **`closer`**.

| Method | Path | Description |
|-------|------|-------------|
| GET | `/closer/` | New referrals vs follow-up |
| GET/POST | `/closer/lead/<id>/process` | Outcome form |

**POST sample — won**

```json
{
  "closer_meeting_status": "برگزار شد",
  "closer_cooperation_status": "موفق",
  "closer_notes": "قرارداد امضا شد"
}
```

Closed deals (won/lost) are not editable unless in follow-up queue.

### 4.8 Search and shared

| Method | Path | Auth | Description |
|-------|------|------|-------------|
| GET | `/search/` | Any logged-in user | Query: `company_name`, `business_type`, `source`, `submit` |
| GET | `/rating-board/modal` | Any logged-in user | HTML fragment for leaderboard |

Search is **not role-filtered** in the current query (all leads matching filters). Treat as an **information-disclosure risk** if untrusted roles should not see the full book (see Security).

### 4.9 Admin (`/admin`) — HTML

Role: **`admin`**.

| Method | Path | Description |
|-------|------|-------------|
| GET | `/admin/` | Hybrid daily + total metrics, user list |
| GET | `/admin/followups` | Follow-up operational view |
| GET | `/admin/archived-leads` | Soft-deleted / rejected archive |
| GET | `/admin/setter-performance` | Setter KPIs |
| GET | `/admin/closer-meetings` | Closer meetings |
| GET | `/admin/sdr-success-calls` | Answered-call list |
| GET/POST | `/admin/bulk-import` | Excel upload |
| GET | `/admin/master-leads` | All non-soft-deleted leads |
| GET/POST | `/admin/lead/<id>/edit` | Full lead edit |
| POST | `/admin/lead/<id>/delete` | Soft delete, then hard delete |
| GET | `/admin/daily-report` | Printable daily report |
| GET | `/admin/employee-daily-report` | Per-employee print |
| GET | `/admin/export/excel/master` | Master workbook |
| GET | `/admin/export/excel/sdr` | SDR department export |
| GET | `/admin/export/excel/setter` | Setter department export |
| GET | `/admin/export/excel/closer` | Closer department export |
| GET/POST | `/admin/users/new` | Create user (password min 6) |
| GET/POST | `/admin/user/<id>/edit` | Edit user |
| POST | `/admin/user/<id>/toggle-active` | Suspend/activate (not self) |
| POST | `/admin/user/<id>/delete` | Delete user (not self); nulls `created_by_id` |
| GET/POST | `/admin/lead-distribution` | Equal assign today vs backlog unassigned stage-2 leads |

**Excel import contract**

- File: `.xlsx` / `.xls`
- Headerless read; **row index 1+** (Excel row 2+)
- Column B = company, C = business type, D = phone
- Source forced to `آپلود اکسل`
- Duplicates skipped via in-memory phone index

**Open-redirect guard on lead edit/delete:** `next` must start with `/admin/`.

### 4.10 Admin JSON endpoint

#### `GET /admin/user/<user_id>/analytics`

| Auth | Admin session |
|------|----------------|
| Success | 200 `application/json` |
| Missing user | 404 JSON |

**Sample response**

```json
{
  "username": "sdr_user",
  "role_label": "SDR",
  "today_count": 3,
  "total_count": 40
}
```

(Exact keys are those returned by `compute_user_performance` plus `username` and `role_label`.)

---

## 5. Configuration & Environment

### 5.1 Configuration class

All runtime settings are loaded from **environment variables** into `app.config.Config` (`app/config.py`). Flask also honors `python-dotenv` if a `.env` file is present (dependency installed; load typically via process manager or shell).

### 5.2 Environment variables

| Variable | Required | Default | Production recommendation |
|----------|----------|---------|---------------------------|
| `SECRET_KEY` | **Yes in production** | `dev-change-me-in-production` | Cryptographically random ≥ 32 bytes; rotate on incident |
| `DATABASE_URL` | No | `sqlite:///<BASE_DIR>/instance/crm.db` | PostgreSQL URI, e.g. `postgresql://user:pass@host:5432/crm_db` |
| `FLASK_DEBUG` | No | `"1"` in `run.py` when unset | **`0`** in production (disables debugger and reloader) |
| `PYTHONUNBUFFERED` | No | — | `1` in containers for log flush |
| `TZ` | No | OS default | `Asia/Tehran` (app also uses `ZoneInfo("Asia/Tehran")` explicitly) |
| `PORT` | Platform | 5000 local / 8000 Gunicorn example | Bind via Gunicorn `--bind` |
| `WEB_CONCURRENCY` | No | — | Gunicorn workers ≈ `(2 × CPU) + 1` |

**Not currently read by code but recommended for ops**

| Variable | Purpose |
|---------|---------|
| `GUNICORN_WORKERS` | Worker count |
| `GUNICORN_TIMEOUT` | Worker timeout (Excel import can be slow) |
| `LOG_LEVEL` | `info` / `warning` |
| `SESSION_COOKIE_SECURE` | Force HTTPS cookies (set in a ProductionConfig subclass) |
| `PREFERRED_URL_SCHEME` | `https` behind TLS terminator |

### 5.3 In-code constants (not env)

| Key | Value | Notes |
|------|-------|-------|
| `SQLALCHEMY_TRACK_MODIFICATIONS` | `False` | Required for Flask-SQLAlchemy |
| `WTF_CSRF_ENABLED` | `True` | Do not disable in production |
| `MAX_CONTENT_LENGTH` | 16 × 1024 × 1024 | Excel uploads |
| `STAGE_LABELS` | 1–5 Persian labels | UI |
| `ROLE_LABELS` | Six roles | UI |
| `PIPELINE_STATUS_LABELS` | Four statuses | UI |
| `ROLE_DASHBOARD` | endpoint names | Post-login routing |
| `login_manager.login_view` | `auth.login` | |
| `login_view` messages | Persian | |

### 5.4 Database URL notes

- SQLAlchemy 1.4+/2.x often expects `postgresql://` (not `postgres://`). If a host injects `postgres://`, rewrite at boot.
- SQLite path is under **`instance/`**, created by the factory (`mkdir`). File is gitignored.
- PostgreSQL: ensure `pg_hba` and TLS as required by the host; use a dedicated role with DML only (no DROP in app runtime).

### 5.5 `.env` example (production)

```env
SECRET_KEY=replace-with-a-long-random-string
FLASK_DEBUG=0
DATABASE_URL=postgresql://crm_app:SECRET@db.internal:5432/crm_db
```

Never commit `.env`. `.gitignore` already lists `.env` and `*.db`.

### 5.6 Demo vs production users

`seed.py` creates:

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | admin |
| `lh_user` | `lh12345` | lh |
| `sdr_user` | `sdr12345` | sdr |
| `setter_user` | `setter12345` | setter |
| `pm_user` | `pm12345` | pm |
| `closer_user` | `closer12345` | closer |

**Production:** do not run seed with demo passwords; create the first admin out-of-band and disable `password_plain`.

### 5.7 Python / OS requirements

- Python **3.10+** (`zoneinfo`, `list[str]` syntax)
- `tzdata` package on Windows for IANA zones
- Optional: Docker, PostgreSQL 14+
- Fonts: `app/static/fonts/Dana-Black.ttf` must be present for branded UI

### 5.8 Dependencies (`requirements.txt`)

| Package | Pin / range | Role |
|---------|-------------|------|
| Flask | 3.0.3 | Web framework |
| Flask-SQLAlchemy | 3.1.1 | ORM integration |
| Flask-WTF | 1.2.1 | CSRF + forms |
| Flask-Login | 0.6.3 | Sessions |
| Flask-Bcrypt | 1.0.1 | Password hashing |
| WTForms | 3.1.2 | Fields/validators |
| email-validator | 2.1.1 | WTForms email (if used) |
| python-dotenv | 1.0.1 | Local env files |
| jdatetime | 5.0.0 | Jalali |
| tzdata | ≥2024.1 | Time zone data |
| pandas | ≥2.0.0 | Excel I/O |
| openpyxl | ≥3.1.0 | xlsx engine |
| gunicorn | unpinned | Linux WSGI |

**Note:** `waitress` is imported in `run_server.py` but **not listed** in `requirements.txt`. Add it if that entrypoint is used.

---

## 6. Deployment & DevOps

### 6.1 Local development

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
python seed.py
python run.py
```

Server: `http://127.0.0.1:5000` with `debug=True` when `FLASK_DEBUG` is not `0`.

**Schema reset (destructive):** `python seed.py --reset`

### 6.2 Production WSGI (Linux)

```bash
export SECRET_KEY=...
export FLASK_DEBUG=0
export DATABASE_URL=postgresql://...
gunicorn run:app --bind 0.0.0.0:8000 --workers 3 --timeout 120 --access-logfile - --error-logfile -
```

`Procfile` for PaaS (Render/Heroku-compatible):

```
web: gunicorn run:app
```

### 6.3 Windows / dedicated IP (`run_server.py`)

Waitress is bound to a **hardcoded** host (`5.57.35.140`) and port `5000`. Treat this as an environment-specific script: parameterize host/port via env before production reuse.

### 6.4 Docker (recommended — not yet in repository)

**Build context:** project root. Persist `instance/` or use Postgres.

**Suggested `Dockerfile`**

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_DEBUG=0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .
RUN mkdir -p instance

RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
```

**Suggested `docker-compose.yml` (PostgreSQL)**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: crm
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: crm_db
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U crm -d crm_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      SECRET_KEY: ${SECRET_KEY}
      FLASK_DEBUG: "0"
      DATABASE_URL: postgresql://crm:${POSTGRES_PASSWORD}@db:5432/crm_db
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

**Build & run**

```bash
docker compose build
docker compose up -d
```

First admin: exec `flask`/`python` one-off to create a user, or a locked-down seed.

### 6.5 Reverse proxy and TLS

Place Nginx or a cloud load balancer in front:

- Terminate TLS (Let’s Encrypt / cloud cert)
- `proxy_pass` to Gunicorn `127.0.0.1:8000`
- Set `client_max_body_size 16m;` (match Flask)
- Forward `X-Forwarded-Proto` and enable `ProxyFix` in Flask if generating absolute URLs
- Security headers: `Strict-Transport-Security`, `X-Content-Type-Options`, `Referrer-Policy`

### 6.6 Kubernetes (target architecture)

| Resource | Recommendation |
|---------|----------------|
| Deployment | 2+ replicas; rolling update |
| Service | ClusterIP :8000 |
| Ingress | TLS, body size 16m |
| Secret | `SECRET_KEY`, `DATABASE_URL` |
| PVC | Only if SQLite (discouraged); prefer managed Postgres |
| HPA | CPU 70% if traffic grows |
| Probes | HTTP GET `/auth/login` (public 200) or a dedicated `/healthz` (to be added) |

SQLite + multiple replicas will **corrupt data**. Use PostgreSQL for any HA layout.

### 6.7 CI/CD strategy (recommended GitHub Actions)

The repository currently has **no `.github/workflows`**. A production pipeline should:

1. **On PR:** `pip install -r requirements.txt`; ruff/flake8; `python -m compileall app`; optional pytest.
2. **On main:** build Docker image; scan (Trivy); push to GHCR; deploy to Render/Fly/K8s.
3. **Never** commit `SECRET_KEY` or `instance/crm.db`.
4. **Do not** run `seed.py --reset` against production.

**Example workflow sketch**

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python -m compileall app seed.py run.py
```

**Render:** connect GitHub, use `Procfile`, set `SECRET_KEY` and `DATABASE_URL` in dashboard. Live demo pattern: `crm-baltazar.onrender.com`.

### 6.8 Backup and operations

| Asset | Action |
|--------|--------|
| SQLite | Stop writes or use `.backup`; copy `instance/crm.db` off-host daily |
| PostgreSQL | `pg_dump` nightly; PITR if RPO requires it |
| Uploads | Excel files are not stored long-term (parsed in request); no object store required today |
| Fonts/static | Bake into image |

### 6.9 Observability

- Gunicorn access/error logs to stdout (12-factor)
- Application errors: Flask 500 pages (add structured logging + Sentry in a later iteration)
- Metrics: no Prometheus exporter yet; admin HTML dashboards are the operational UI

---

## 7. Security & Error Handling

### 7.1 Authentication strategy

| Control | Implementation |
|--------|----------------|
| Credential store | `users.password_hash` via Flask-Bcrypt |
| Session | Flask-Login; `user_loader` loads only **active** users (`is_active`) |
| Login | Username lookup + `check_password`; suspended accounts see Persian danger flash |
| Logout | `logout_user()` |
| Password policy | Admin create/edit: min length **6** (raise to 12+ for production policy) |

**Session cookie (Flask defaults)**

- Signed with `SECRET_KEY`
- `HttpOnly` (Flask default)
- `SameSite` / `Secure` should be set explicitly in production (`SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_SAMESITE=Lax`)

### 7.2 Authorization

- `@role_required(*roles)` — unauthenticated → login; wrong role → **403**
- SDR extra: cannot process another agent’s assigned lead
- LH extra: wrong-number fix only for own `created_by_id`
- Admin cannot suspend or delete **self**
- Lead `next` redirects restricted to `/admin/` prefix (open-redirect mitigation)

### 7.3 CSRF, CORS, uploads

| Topic | Status |
|--------|--------|
| CSRF | `CSRFProtect` + Flask-WTF on all forms |
| CORS | **Not applicable** as a first-party same-origin SSR app. If a future SPA is added, whitelist origins explicitly; do not use `*` with credentials |
| File upload | Extension allow-list `xlsx`/`xls`; 16 MB cap |
| Excel parse | Broad `except Exception` with user-facing flash (avoid leaking stack traces) |

### 7.4 Input validation

- WTForms `DataRequired`, `Length`, `Optional`, custom `ValidationError`
- Phone: Persian/Arabic digit translation, digit-only storage, leading `0` for `9…` mobiles, duplicate check across three slots
- PM amount: `float`, reject negatives
- Jalali dates parsed strictly `Y/M/D`
- Search: `ILIKE` with user substring — **parameterized** via SQLAlchemy (no string-concat SQL)

### 7.5 Encryption and secrets

- Passwords: bcrypt (not reversible)
- **Gap:** `password_plain` stores the same password in cleartext for admin convenience. This defeats hashing if the DB is leaked. **Production requirement:** remove column, stop writing plaintext, and never display live passwords.
- TLS: terminate at proxy; Flask itself does not implement HTTPS
- `SECRET_KEY` default is unsafe; production **must** override

### 7.6 Security best practices applied vs. gaps

**Applied**

- Bcrypt hashing
- CSRF on state-changing forms
- RBAC decorator
- Inactive user cannot be loaded into session
- Upload type and size limits
- Soft-delete instead of casual hard-delete
- Parameterized ORM queries

**Must-fix / harden for enterprise**

| Risk | Severity | Mitigation |
|------|---------|------------|
| `password_plain` | Critical | Remove field; use password-reset flow |
| Default `SECRET_KEY` | Critical | Fail boot if default detected when `FLASK_DEBUG=0` |
| Tailwind CDN + no SRI | Medium | Self-host built CSS |
| Search not scoped by role | Medium | Filter by role/ownership |
| Phone uniqueness in Python | Medium | Unique index on normalized phone |
| No rate limit on `/auth/login` | Medium | Proxy rate limit / Flask-Limiter |
| No security headers in-app | Low | Nginx or `flask-talisman` |
| `run_server.py` hardcoded IP | Low | Env-based bind |
| Waitress not in requirements | Low | Pin dependency |
| Admin JSON analytics | Low | Ensure no extra PII beyond performance stats |

### 7.7 Error handling

| Mechanism | Behavior |
|----------|----------|
| `@app.errorhandler(403)` | Custom Persian 403 template |
| `abort(404)` | Flask default 404 (add branded 404 template later) |
| Flash categories | `success`, `danger`, `warning`, `info` |
| Login manager | Persian “must log in” warning |
| Excel import | Caught exception → flash, no 500 to user |
| User loader | Returns `None` if inactive → session dropped |

Unhandled exceptions still yield generic 500 in production if debug is off.

### 7.8 Troubleshooting / FAQ

**Q: Login loops or “must log in” on every page**  
A: Cookies blocked, wrong `SECRET_KEY` rotated while sessions exist (users must log in again), or `is_active=False`.

**Q: `sqlite3.OperationalError: no such column`**  
A: Restart the app so `apply_schema_patches()` runs, or `python seed.py --reset` on a **non-production** DB.

**Q: SDR cannot see a new LH lead**  
A: Leads enter the **unassigned pool**. Admin must run **Lead distribution** (`/admin/lead-distribution`) for today and/or backlog. Automatic `assign_sdr_to_lead` exists in code for seed/least-load but **LH intake** uses `send_lead_to_sdr_pool` (clears assignment).

**Q: Duplicate phone still inserted**  
A: Check archived vs `active_only()` — duplicates are ignored for **non-deleted** leads only. Soft-deleted phones can be reused.

**Q: Gunicorn multiple workers + SQLite lock / corruption**  
A: Move to PostgreSQL; SQLite is for single-node/dev.

**Q: Jalali date rejected on PM form**  
A: Use `YYYY/MM/DD` with valid Jalali calendar values; conversion uses `jdatetime`.

**Q: 413 on Excel upload**  
A: File > 16 MB or proxy `client_max_body_size` too small.

**Q: 403 on a dashboard**  
A: User `role` does not match blueprint (e.g. SDR opening `/admin/`).

**Q: Scores did not increase**  
A: Points award only when Setter status **newly** becomes `تایید شده`, and LH/SDR users are active with matching roles.

**Q: Production still shows demo users**  
A: `seed.py` was run against the production database. Recreate users, rotate all passwords, rotate `SECRET_KEY`.

**Q: Render/Heroku dyno sleeps / ephemeral disk**  
A: SQLite on ephemeral filesystem **loses data**. Attach Postgres (`DATABASE_URL`).

**Q: Fonts missing / fallback sans**  
A: Ensure `app/static/fonts/Dana-Black.ttf` is deployed with the image.

---

## Appendix A — Pipeline cheat sheet

| Stage | Role | Primary actions |
|-------|--------|-----------------|
| 1 | LH | Intake; fix wrong numbers |
| 2 | SDR | Call; route Setter / PM / follow-up / disqualify |
| 3 | Setter | Approve → Closer + scores; reject; uncertain |
| 4 | PM | Submit proposal → SDR proposal follow-up |
| 5 | Closer | Won / lost / follow-up |

## Appendix B — Related documents

- Product README: `README.md`
- License: `LICENSE`
- Code entry: `app/__init__.py`, `app/models.py`

---

*End of Technical Specification & Architecture Document — Baltazar CRM v1.0.0*

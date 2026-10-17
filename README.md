<div align="center">

# Sales Pipeline CRM

**A sequential sales pipeline CRM with role-based dashboards — LH → SDR → Setter → PM → Closer, plus Admin.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

</div>

---

## About

This project was **created and developed by Asal Najafizadeh**.

The folder name *Baltazar* (and any similar label in the repository path) is **only a random placeholder** — it is not a company, product brand, or team name. The application itself is a generic self-hosted CRM.

The CRM addresses **unstructured, multi-stage sales pipelines** with a single sequential workflow: **Lead Hunter (LH) → SDR → Setter → PM → Closer**, plus an **Admin** role for operations and reporting. Each role gets a dedicated dashboard and queue; admins see the full funnel, daily metrics, and Excel import/export.

---

## Key features

- **Sequential 5-stage pipeline** — LH → SDR → Setter → PM → Closer with enforced stage transitions.
- **Role-based dashboards** — Tailored views for LH, SDR, Setter, PM, Closer, and Admin.
- **Lead intake with duplicate detection** — Up to three phone numbers per lead, primary-phone marking, duplicate rejection.
- **SDR call workflow** — Answered / unanswered / wrong-number; route to Setter, PM, follow-up, or disqualify.
- **Wrong-number correction loop** — Returns leads to LH for correction and re-queues to SDR.
- **Setter meeting management** — Approve, reject, or uncertain; approved meetings advance to Closer and award **+1 score** to LH and SDR.
- **PM proposal submission** — Jalali (Persian) dates, amount validation, proposal tracking.
- **Closer deal closing** — Won / lost / follow-up with closing notes.
- **Admin analytics** — Daily and cumulative metrics across the funnel.
- **Automated lead distribution** — Equal distribution of unassigned leads among active SDRs.
- **Excel import/export** — Bulk import and department or per-user exports.
- **User management** — Create, edit, suspend, and delete users with role assignment.
- **Lead search** — Filter by company name, business type, and source.
- **Rating board / leaderboard** — Performance scoring.
- **Jalali calendar** — Persian date support via `jdatetime`.
- **Security** — Bcrypt, Flask-Login sessions, CSRF protection.
- **Soft-delete / archive** — Archived leads with audit trail.

---

## Built with

| Category       | Technology |
|----------------|------------|
| **Language**   | Python 3.10+ |
| **Framework**  | Flask 3.0.3 |
| **ORM**        | SQLAlchemy 2.x |
| **Database**   | SQLite (default) or PostgreSQL via `DATABASE_URL` |
| **Forms**      | WTForms |
| **Auth**       | Flask-Login, Flask-Bcrypt |
| **Dates**      | jdatetime |
| **Excel**      | pandas, openpyxl |
| **Server**     | Gunicorn (production) |

---

## Getting started

### Prerequisites

- Python 3.10+
- pip
- Git
- *(Optional)* PostgreSQL if you do not use the default SQLite database

### Installation

```bash
git clone <your-repository-url>
cd <repository-directory>
```

#### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
python seed.py
python run.py
```

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python seed.py
python run.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

After schema changes, reset the database with:

```bash
python seed.py --reset
```

### Environment

Create a `.env` file in the project root:

```env
SECRET_KEY=your-production-secret-key
FLASK_DEBUG=0
# DATABASE_URL=postgresql://user:password@localhost:5432/crm_db
```

Never commit real secrets to version control.

---

## Demo logins

After `python seed.py`:

| Username      | Password      | Role   |
|---------------|---------------|--------|
| `admin`       | `admin123`    | Admin  |
| `lh_user`     | `lh12345`     | LH     |
| `sdr_user`    | `sdr12345`    | SDR    |
| `setter_user` | `setter12345` | Setter |
| `pm_user`     | `pm12345`     | PM     |
| `closer_user` | `closer12345` | Closer |

These credentials are for **local development only**. Change all passwords in production.

---

## Production

```bash
gunicorn run:app --bind 0.0.0.0:8000 --workers 3
```

Set `SECRET_KEY` and, if needed, `DATABASE_URL` on your host.

---

## Pipeline flow

| Stage | Role   | Action |
|-------|--------|--------|
| 1     | LH     | Intake → SDR pool |
| 2     | SDR    | Call → Setter / PM / follow-up / disqualify |
| 3     | Setter | Meeting → approve (→ Closer) / reject / uncertain |
| 4     | PM     | Proposal sent |
| 5     | Closer | Won / lost / follow-up |

---

## Contributing

Contributions are welcome. Fork the repository, create a feature branch, commit your changes, and open a pull request.

---

## License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Author:** Asal Najafizadeh

</div>
